from flask import jsonify
from app.api import api
from app.models.test import Test
from app.models.booking import Booking

@api.route("/tests", methods=["GET"])
def api_tests():
    tests = Test.query.all()
    return jsonify([{"id": t.id, "name": t.name, "price": t.price} for t in tests])


@api.route("/bookings/<int:booking_id>", methods=["GET"])
def api_booking(booking_id):
    b = Booking.query.get_or_404(booking_id)
    return jsonify({
        "id": b.id,
        "status": b.status,
        "patient": b.patient.full_name,
        "tests": [item.test.name for item in b.items]
    })