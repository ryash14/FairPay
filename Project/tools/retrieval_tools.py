"""Reads the advice a remediation guide gives the employee."""
from config import config
from knowledge.vector_index import search_document


def read_employee_steps(collection, query_category):
    """The passages of this category's own guide closest to the employee-steps question, closest first."""
    guide = config.GUIDE_DOCUMENT_BY_CATEGORY[query_category]
    return search_document(collection, config.EMPLOYEE_STEPS_QUESTION, guide, config.EMPLOYEE_STEPS_RESULT_COUNT)
