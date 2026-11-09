"""Recalls the last few exchanges of a person's own conversation."""
from config import config
from persistence import repository
from persistence.models import ChatTurn

FIRST_QUESTION = "This is the first question in the conversation."


def recall_conversation(session, username, question_text):
    """history_text for the prompt and search_text for retrieval, from this person's own recent turns only."""
    turns = repository.fetch_chat_turns(session, ChatTurn.username == username, config.CHAT_HISTORY_TURN_LIMIT)
    turns = list(reversed(turns))
    if not turns:
        return {"history_text": FIRST_QUESTION, "search_text": question_text}
    blocks = []
    for turn in turns:
        answer = (config.CHAT_STATUS_ANSWER_IN_HISTORY if turn["question_type"] == config.CHAT_TYPE_QUERY_STATUS
                  else turn["answer_text"])
        blocks.append(f"Asked: {turn['question_text']}\nAnswered: {answer}")
    return {"history_text": "\n\n".join(blocks),
            "search_text": " ".join([turn["question_text"] for turn in turns] + [question_text])}
