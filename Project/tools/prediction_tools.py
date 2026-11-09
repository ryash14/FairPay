"""Turns a model's raw output into the facts the business acts on."""
from collections import Counter

import pandas as pd

from config import config
from data_pipeline.feature_builder import build_feature_frame


def _band(probability):
    if probability >= config.CORRECTION_BAND_HIGH_THRESHOLD:
        return config.CORRECTION_BAND_HIGH
    if probability >= config.CORRECTION_BAND_MEDIUM_THRESHOLD:
        return config.CORRECTION_BAND_MEDIUM
    return config.CORRECTION_BAND_LOW


def build_correction_facts(correction_model, correction_feature_names, queries):
    """Each query's probability of a pay correction, rounded, and the band it falls in."""
    features = build_feature_frame(queries, config.CORRECTION_NUMERIC_FEATURES, config.CORRECTION_CATEGORICAL_FEATURES)
    features = features[list(correction_feature_names)]
    probabilities = correction_model.predict_proba(features)[:, 1]
    facts = []
    for probability in probabilities:
        rounded = round(float(probability), config.PROBABILITY_DECIMALS)
        facts.append({"correction_probability": rounded, "correction_band": _band(rounded)})
    return facts


def build_category_facts(category_model, note_texts):
    """The category most readable notes name, how far they agree, and what else was named."""
    readable = [text for text in note_texts if len(str(text).split()) >= config.MINIMUM_NOTE_WORDS]
    if not readable:
        raise ValueError(f"No employee note has the {config.MINIMUM_NOTE_WORDS} words the category model needs to "
                         f"read it")
    probabilities = category_model.predict_proba(readable)
    classes = [str(c) for c in category_model.classes_]
    note_categories = [classes[row.argmax()] for row in probabilities]
    votes = Counter(note_categories)
    most = max(votes.values())
    tied = [category for category, count in votes.items() if count == most]
    summed = {category: float(probabilities[:, classes.index(category)].sum()) for category in tied}
    query_category = max(tied, key=lambda category: summed[category])
    return {
        "query_category": query_category,
        "agreement": round(votes[query_category] / len(readable), config.PROBABILITY_DECIMALS),
        "notes_read": int(len(readable)),
        "notes_too_short_to_read": int(len(note_texts) - len(readable)),
        "note_categories": note_categories,
        "other_categories": sorted(category for category in votes if category != query_category),
    }


def estimate_remediation_effort(effort_model, effort_feature_names, query_profile, correction_band, query_category,
                                pay_pieces, money_at_stake_aud):
    """Analyst hours for the remediation, the interpreter applied once afterwards, and the senior line."""
    source = query_profile[config.VERIFIED_HOURS_SOURCE_COLUMN]
    if source not in config.VERIFIED_HOURS_SOURCES:
        raise ValueError(f"{config.VERIFIED_HOURS_SOURCE_COLUMN} must be one of {config.VERIFIED_HOURS_SOURCES}, "
                         f"not {source}")
    interpreter = query_profile[config.INTERPRETER_COLUMN]
    if interpreter not in (config.BOOLEAN_YES, config.BOOLEAN_NO):
        raise ValueError(f"{config.INTERPRETER_COLUMN} must be Yes or No, not {interpreter}")

    def yes_if(found):
        return config.BOOLEAN_YES if found else config.BOOLEAN_NO

    inputs = dict(query_profile)
    inputs.update(config.EFFORT_PLANNING_ASSUMPTIONS)
    inputs.update({
        "query_category": query_category,
        "correction_band": correction_band,
        "period_pieces_count": len(pay_pieces),
        "classifications_involved_count": len({piece["classification"] for piece in pay_pieces}
                                              | {query_profile[config.PAID_CLASSIFICATION_COLUMN]}),
        "amount_at_stake_aud": float(money_at_stake_aud),
        "clock_records_obtained_flag": config.BOOLEAN_YES,
        "manager_interview_required_flag": yes_if(source in config.MANAGER_INTERVIEW_HOURS_SOURCES),
        "vendor_audit_required_flag": yes_if(source in config.VENDOR_AUDIT_HOURS_SOURCES),
        "venue_manager_involved_flag": yes_if(source in config.VENUE_MANAGER_HOURS_SOURCES),
        config.INTERPRETER_COLUMN: config.BOOLEAN_NO,
    })
    frame = build_feature_frame(pd.DataFrame([inputs]), config.EFFORT_NUMERIC_FEATURES,
                                config.EFFORT_CATEGORICAL_FEATURES)[list(effort_feature_names)]
    base = float(effort_model.predict(frame)[0])
    applied = interpreter == config.BOOLEAN_YES
    needed = base * config.INTERPRETER_EFFORT_MULTIPLIER if applied else base
    needed = round(needed, config.EFFORT_HOURS_DECIMALS)
    return {
        "base_hours": round(base, config.EFFORT_HOURS_DECIMALS),
        "multiplier_applied": bool(applied),
        "effort_needed_hours": needed,
        "senior_review_required": bool(needed > config.SENIOR_REVIEW_THRESHOLD_HOURS),
        "planning_assumptions": dict(config.EFFORT_PLANNING_ASSUMPTIONS),
    }
