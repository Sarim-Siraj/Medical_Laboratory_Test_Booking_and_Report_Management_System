from app import db


class TestCategory(db.Model):

    __tablename__ = "test_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    tests = db.relationship("Test", back_populates="category")

    def __repr__(self):
        return f"<TestCategory {self.name}>"


class Test(db.Model):

    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("test_categories.id"),
        nullable=False
    )

    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    sample_type = db.Column(db.String(50), nullable=True)
    turnaround_hours = db.Column(db.Integer, nullable=True)

    category = db.relationship("TestCategory", back_populates="tests")

    def __repr__(self):
        return f"<Test {self.name}>"