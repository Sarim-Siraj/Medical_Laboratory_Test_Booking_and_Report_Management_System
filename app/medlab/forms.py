from flask_wtf import FlaskForm

from wtforms import (
    StringField,
    SelectField,
    SelectMultipleField,
    SubmitField,
    DateField
)

from wtforms.validators import (
    DataRequired,
    Optional,
    Regexp,
    Length
)


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


class ResultEntryForm(FlaskForm):

    parameter = StringField(
        "Parameter",
        validators=[
            DataRequired(message="Parameter name is required."),
            Length(min=2, max=100, message="Parameter must be 2-100 characters.")
        ]
    )

    value = StringField(
        "Value",
        validators=[
            DataRequired(message="Result value is required."),
            Length(max=50, message="Value is too long.")
        ]
    )

    unit = StringField(
        "Unit",
        validators=[
            Optional(),
            Length(max=20, message="Unit is too long.")
        ]
    )


class WalkInPatientForm(FlaskForm):

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(
                message="Patient name is required."
            ),
            Length(
                min=3,
                max=100,
                message="Name must be 3-100 characters."
            )
        ]
    )

    phone = StringField(
        "Phone",
        validators=[
            Optional(),
            Regexp(
                r'^\d{10,15}$',
                message="Phone must contain only digits (10-15 numbers)."
            )
        ]
    )

    address = StringField(
        "Address",
        validators=[
            Optional(),
            Length(
                max=255,
                message="Address is too long."
            )
        ]
    )

    dob = DateField(
        "Date of Birth",
        format="%Y-%m-%d",
        validators=[
            Optional()
        ]
    )

    gender = SelectField(
        "Gender",
        choices=[
            ("", "Select Gender"),
            ("Male", "Male"),
            ("Female", "Female"),
            ("Other", "Other")
        ],
        validators=[
            Optional()
        ]
    )

    submit = SubmitField("Register Patient")