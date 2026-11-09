"""Cuts documents into numbered sections, and sections into passages cut only at sentence ends."""
import re

from config import config


def split_documents_into_sections(document_entries):
    """One entry per numbered section, with the header line removed and whitespace tidied."""
    sections = []
    for entry in document_entries:
        name, text = entry["document_name"], entry["document_text"]
        headers = re.findall(config.DOCUMENT_HEADER_PATTERN, text)
        if len(headers) != 1:
            raise ValueError(f"{name} carries {len(headers)} header lines instead of one")
        text = re.sub(config.DOCUMENT_HEADER_PATTERN, " ", text)
        headings = list(re.finditer(config.SECTION_HEADING_PATTERN, text))
        numbers = [int(match.group(1)) for match in headings]
        if not numbers or numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f"{name} is not divided into sections numbered from 1: {numbers}")
        cuts = [0] + [match.start() for match in headings[1:]] + [len(text)]
        for start, end in zip(cuts, cuts[1:]):
            section = re.sub(config.CONTROL_CHARACTER_PATTERN, " ", text[start:end])
            section = re.sub(config.WHITESPACE_RUN_PATTERN, " ", section).strip()
            sections.append({"document_name": name, "section_text": section})
    return sections


def build_chunk_records(section_entries, chunk_size, chunk_overlap):
    """Passages of whole sentences, neighbours sharing up to chunk_overlap characters of whole sentences."""
    records = []
    counters = {}

    def close(name, sentences):
        number = counters.get(name, 0)
        counters[name] = number + 1
        records.append({"chunk_id": f"{name}-{number}", "chunk_text": " ".join(sentences), "document_name": name})

    for entry in section_entries:
        name = entry["document_name"]
        sentences = [s for s in re.split(config.SENTENCE_BOUNDARY_PATTERN, entry["section_text"]) if s and s.strip()]
        current, length = [], 0
        for sentence in sentences:
            if current and length + len(sentence) > chunk_size:
                close(name, current)
                carried, carried_length = [], 0
                for previous in reversed(current):
                    if carried_length + len(previous) + 1 > chunk_overlap:
                        break
                    carried.insert(0, previous)
                    carried_length += len(previous) + 1
                current, length = carried, carried_length
            current.append(sentence)
            length += len(sentence) + 1
        if current:
            close(name, current)
    return records
