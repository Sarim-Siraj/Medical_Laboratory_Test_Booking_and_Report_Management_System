from flask_wtf import FlaskForm
from wtforms import SelectField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired


class BookingForm(FlaskForm):

    patient_id = SelectField(
        "Patient",
        coerce=int,
        validators=[DataRequired()]
    )

    test_ids = SelectMultipleField(
        "Select Tests",
        coerce=int,
        validators=[DataRequired()]
    )

    submit = SubmitField("Book Tests")