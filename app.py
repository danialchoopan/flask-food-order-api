from flask import Flask, request, jsonify
from models import db, User, Seller, Food, Order, OrderDetail
from auth import register_user, register_seller, login_user, login_seller, token_required_seller, token_required_user
from flask_cors import CORS
from base64 import b64decode


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/upload'  # مسیر ذخیره تصاویر
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()


# ثبت و ورود
@app.route("/user/register", methods=["POST"])
def user_register():
    return register_user()


@app.route("/user/login", methods=["POST"])
def user_login():
    return login_user()


@app.route("/seller/register", methods=["POST"])
def seller_register():
    return register_seller()


@app.route("/seller/login", methods=["POST"])
def seller_login():
    return login_seller()


# ویرایش کاربر شهر و رمزعبور
@app.route("/user/edit/password", methods=["POST"])
@token_required_user
def edit_user_password():
    data = request.json
    new_password = data.get("new_password")
    old_password = data.get("old_password")

    user = User.query.get_or_404(request.user.id)

    if not user.check_password(old_password):
        return jsonify({"success": False, "message": "رمزعبور وارد شده شما اشتباه است"}), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"success": True}), 200


@app.route("/user/edit/city", methods=["POST"])
@token_required_user
def edit_user_city():
    data = request.json
    new_city = data.get("new_city_name")

    if not new_city:
        return jsonify({"success": False}), 400

    user = User.query.get_or_404(request.user.id)
    user.city_name = new_city
    db.session.commit()
    return jsonify({"success": True}), 200


# ویرایش فروشنده شهر و رمزعبور
@app.route("/seller/edit/password", methods=["POST"])
@token_required_seller
def edit_seller_password():
    data = request.json
    new_password = data.get("new_password")
    old_password = data.get("old_password")

    seller = Seller.query.get_or_404(request.seller.id)

    if not seller.check_password(old_password):
        return jsonify({"success": False, "message": "رمزعبور وارد شده شما اشتباه است"}), 400

    seller.set_password(new_password)
    db.session.commit()

    return jsonify({"success": True}), 200


@app.route("/seller/edit/city", methods=["POST"])
@token_required_seller
def edit_seller_city():
    data = request.json
    new_city = data.get("new_city_name")

    if not new_city:
        return jsonify({"success": False}), 400

    seller = Seller.query.get_or_404(request.seller.id)
    seller.city_name = new_city
    db.session.commit()
    return jsonify({"success": True}), 200


# تمامی فروشگاه های اطراف
@app.route("/user/restaurants", methods=["GET"])
@token_required_user
def get_restaurants():
    user = User.query.get_or_404(request.user.id)
    sellers = Seller.query.filter_by(city_name=user.city_name).all()

    restaurants = [
        {
            "id": seller.id,
            "name": seller.restaurant_name,
            "category": seller.category,
            "address": seller.address,
            "open": seller.open,
            "image": f"/images/restaurants/{seller.id}.jpg"  # Assuming images are named by seller ID
        }
        for seller in sellers
    ]

    return jsonify({"success": True, "restaurants": restaurants}), 200


@app.route("/user/restaurant/<int:id>", methods=["GET"])
@token_required_user
def get_restaurant_by_id(id):
    seller = Seller.query.get_or_404(id)
    seller_foods = Food.query.filter_by(seller_id=seller.id).all()
    restaurants = {
        "seller_id": seller.id,
        "restaurant_name": seller.restaurant_name,
        "restaurant_category": seller.category,
        "restaurant_address": seller.address,
        "restaurant_open": seller.open,
        "restaurant_image": f"/images/restaurants/{seller.id}.jpg",
        "foods": [  # List of food dictionaries
            {
                "food_id": food.id,
                "food_name": food.name,
                "food_price": food.price,
                "food_availability": food.availability,
                "food_description": food.description,
                "food_image": f"/images/food/{food.id}.jpg",  # Assuming images are named by food ID
            }
            for food in seller_foods
        ]
    }
    return jsonify({"success": True, "restaurants": restaurants}), 200


# بررسی نوع فایل مجاز
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# تغییر وضعیت فروشگاه

@app.route("/seller/open", methods=["POST"])
@token_required_seller
def seller_edit_open():
    data = request.json
    open_seller = data.get("open")
    seller = Seller.query.get_or_404(request.seller.id)
    seller.open = open_seller
    db.session.commit()
    return jsonify({"success": True, "seller_open": seller.open}), 200

@app.route("/seller/open/status", methods=["GET"])
@token_required_seller
def seller_open_status():
    seller = Seller.query.get_or_404(request.seller.id)
    return jsonify({"success": True, "seller_open": seller.open}), 200


# اپلود تصویر فروشنده
@app.route('/seller/upload_image', methods=['POST'])
@token_required_seller
def upload_image():
    if 'image' not in request.files:
        return jsonify({"message": "تصویری ارسال نشده است."}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"message": "نام فایل خالی است."}), 400

    if not allowed_file(file.filename):
        return jsonify({"message": "فرمت فایل مجاز نیست. فقط png، jpg و jpeg پشتیبانی می‌شوند."}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # به‌روزرسانی تصویر فروشنده
    request.seller.image = file_path
    db.session.commit()

    return jsonify({"message": "تصویر با موفقیت آپلود شد.", "image_url": file_path}), 200


# CRUD غذاها
@app.route("/seller/foods", methods=["POST"])
@token_required_seller
def add_food():
    data = request.json

    # Check for required fields
    if not all(key in data for key in ["name", "photo", "description", "price"]):
        return jsonify({"error": "Missing required fields"}), 400

    photo_data = data.get("photo")
    if photo_data:
        try:
            # Decode base64 image data
            image_data = b64decode(photo_data.split(",")[-1])

            # Create directory if it doesn't exist
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Generate a secure file name
            image_filename = secure_filename(f"{data['name']}_image.jpg")
            image_path = os.path.join(UPLOAD_FOLDER, image_filename)

            # Save the image
            with open(image_path, "wb") as image_file:
                image_file.write(image_data)
        except Exception as e:
            return jsonify({"error": f"Invalid image data: {str(e)}"}), 400
    else:
        image_path = None

    # Create the Food instance
    food = Food(
        seller_id=request.seller.id,
        name=data["name"],
        photo=image_path,  # Save the file path in the database
        description=data["description"],
        price=data["price"],
        availability=data.get("availability", True)
    )
    db.session.add(food)
    db.session.commit()

    return jsonify({"message": "غذا اضافه شد.", "food_id": food.id}), 201

@app.route("/seller/food/<int:id>", methods=["GET"])
@token_required_seller
def get_food(id):
    food = Food.query.get_or_404(id)  # Filter by seller_id
    return jsonify({
        "foods": {
            "id": food.id,
            "name": food.name,
            "description": food.description,
            "price": food.price,
            "photo": food.photo.replace("\\", "/"),
            "availability": food.availability,
            "seller_id": food.seller_id
        },
        "success": "true"
    }), 200

@app.route("/seller/foods", methods=["GET"])
@token_required_seller
def get_foods():
    foods = Food.query.filter_by(seller_id=request.seller.id).all()  # Filter by seller_id
    return jsonify({
        "foods": [{
            "id": food.id,
            "name": food.name,
            "description": food.description,
            "price": food.price,
            "photo": food.photo.replace("\\", "/"),
            "availability": food.availability,
            "seller_id": food.seller_id
        } for food in foods],
        "success": "true"
    }), 200




@app.route("/seller/food/<int:food_id>", methods=["PUT"])
@token_required_seller
def update_food(food_id):
    data = request.json
    # Check if the food exists
    food = Food.query.filter_by(id=food_id, seller_id=request.seller.id).first()
    if not food:
        return jsonify({"error": "غذا پیدا نشد."}), 404

    # Check for required fields
    if not any(key in data for key in ["name", "photo", "description", "price", "availability"]):
        return jsonify({"error": "لطفا حداقل یک فیلد برای بروزرسانی ارسال کنید."}), 400

    # Update photo if provided
    if "photo" in data:
        photo_data = data["photo"]
        if photo_data:
            try:
                # Decode base64 image data
                image_data = b64decode(photo_data.split(",")[-1])

                # Create directory if it doesn't exist
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                # Generate a secure file name
                image_filename = secure_filename(f"{food.name}_image.jpg")
                image_path = os.path.join(UPLOAD_FOLDER, image_filename)

                # Save the image
                with open(image_path, "wb") as image_file:
                    image_file.write(image_data)

                # Update the food's photo path
                food.photo = image_path
            except Exception as e:
                return jsonify({"error": f"Invalid image data: {str(e)}"}), 400

    # Update other fields
    if "name" in data:
        food.name = data["name"]
    if "description" in data:
        food.description = data["description"]
    if "price" in data:
        food.price = data["price"]
    if "availability" in data:
        food.availability = data["availability"]

    # Commit the changes
    db.session.commit()

    return jsonify({"message": "غذا با موفقیت بروزرسانی شد.", "food_id": food.id}), 200


@app.route("/seller/foods/<int:food_id>", methods=["DELETE"])
@token_required_seller
def delete_food(food_id):
    """Delete a food item."""
    food = Food.query.get_or_404(food_id)

    # Check if the food belongs to the current seller
    if food.seller_id != request.seller.id:
        return jsonify({"message": "شما مجاز به حذف این غذا نیستید."}), 403

    db.session.delete(food)
    db.session.commit()
    return jsonify({"message": "غذا حذف شد."}), 200

# CRUD سفارشات
@app.route("/orders", methods=["POST"])
@token_required_user
def place_order():
    """افزودن سفارش جدید"""
    data = request.json
    if not data.get("seller_id") or not data.get("details") or not isinstance(data["details"], list):
        return jsonify({"message": "اطلاعات سفارش ناقص است."}), 400

    total_price = 0
    for item in data["details"]:
        food = Food.query.get(item["food_id"])
        if not food or not food.availability:
            return jsonify({"message": f"غذا با آی‌دی {item['food_id']} موجود نیست."}), 400
        total_price += food.price * item["quantity"]

    new_order = Order(
        user_id=request.seller.id,  # از توکن کاربر
        seller_id=data["seller_id"],
        total_price=total_price,
        status="در حال پردازش"
    )
    db.session.add(new_order)
    db.session.commit()

    for item in data["details"]:
        order_detail = OrderDetail(
            order_id=new_order.id,
            food_id=item["food_id"],
            quantity=item["quantity"],
            price=Food.query.get(item["food_id"]).price
        )
        db.session.add(order_detail)
    db.session.commit()

    return jsonify({"message": "سفارش با موفقیت ثبت شد.", "order_id": new_order.id}), 201


@app.route("/orders", methods=["GET"])
@token_required_user
def get_user_orders():
    """دریافت لیست سفارش‌های کاربر"""
    orders = Order.query.filter_by(user_id=request.seller.id).all()
    return jsonify([{
        "id": order.id,
        "order_date": order.order_date,
        "total_price": order.total_price,
        "status": order.status,
        "details": [{
            "food_id": detail.food_id,
            "quantity": detail.quantity,
            "price": detail.price
        } for detail in order.details]
    } for order in orders]), 200


@app.route("/orders/<int:order_id>", methods=["PUT"])
@token_required_user
def update_order(order_id):
    """ویرایش وضعیت سفارش"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != request.seller.id:
        return jsonify({"message": "شما مجاز به ویرایش این سفارش نیستید."}), 403

    data = request.json
    order.status = data.get("status", order.status)
    db.session.commit()
    return jsonify({"message": "وضعیت سفارش با موفقیت ویرایش شد."}), 200


@app.route("/orders/<int:order_id>", methods=["DELETE"])
@token_required_user
def delete_order(order_id):
    """حذف سفارش"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != request.seller.id:
        return jsonify({"message": "شما مجاز به حذف این سفارش نیستید."}), 403

    # حذف جزئیات سفارش
    OrderDetail.query.filter_by(order_id=order.id).delete()
    # حذف سفارش
    db.session.delete(order)
    db.session.commit()
    return jsonify({"message": "سفارش با موفقیت حذف شد."}), 200


# راه‌اندازی سرور
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # ایجاد جداول در پایگاه‌داده
    app.run(debug=True)
