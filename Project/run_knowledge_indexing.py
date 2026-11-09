"""Step 4: build the knowledge base from the sixteen documents, then read every rate back out of it.

    python run_knowledge_indexing.py
"""
from config import config


def describe_window(window):
    if "night_rate_aud" in window:
        hourly = f"day AUD {window['day_rate_aud']}, night AUD {window['night_rate_aud']} an hour"
    else:
        hourly = f"AUD {window['ordinary_rate_aud']} an hour"
    return f"    from {window['opens_on']}: {hourly}, site allowance AUD {window['site_allowance_aud']} a day"


def main():
    from knowledge.chunk_splitting import build_chunk_records, split_documents_into_sections
    from knowledge.pdf_extraction import extract_text_from_directory
    from knowledge.schedule_reading import read_commitment_payments, read_pay_schedule
    from knowledge.vector_index import build_vector_index, open_vector_index

    print("building the payroll knowledge index")
    documents = extract_text_from_directory(config.DOCS_DIRECTORY)
    sections = split_documents_into_sections(documents)
    chunks = build_chunk_records(sections, config.CHUNK_SIZE_CHARACTERS, config.CHUNK_OVERLAP_CHARACTERS)
    stored = build_vector_index(chunks, config.VECTOR_STORE_DIRECTORY, config.VECTOR_COLLECTION_NAME)
    print(f"documents read: {len(documents)}")
    print(f"sections found: {len(sections)}")
    print(f"chunks stored:  {stored}")
    print(f"store location: {config.VECTOR_STORE_DIRECTORY}")

    collection = open_vector_index(config.VECTOR_STORE_DIRECTORY, config.VECTOR_COLLECTION_NAME)
    print()
    print("rates read from each classification's own pay schedule")
    for classification, document in config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION.items():
        schedule = read_pay_schedule(collection, classification)
        print(f"  {classification} ({document})")
        for window in schedule["rate_windows"]:
            print(describe_window(window))
        if schedule["moves_onto"]:
            print(f"    when the traineeship ends the employee moves to {schedule['moves_onto']}")
    print()
    print(f"payroll commitment payments ({config.COMMITMENTS_DOCUMENT})")
    for code, payment in read_commitment_payments(collection).items():
        print(f"  {code}: AUD {payment}")


if __name__ == "__main__":
    main()
