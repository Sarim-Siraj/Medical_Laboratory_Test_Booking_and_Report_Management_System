from flask import Blueprint

medlab = Blueprint(
    "medlab",
    __name__,
    url_prefix="/medlab"
)