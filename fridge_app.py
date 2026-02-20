import streamlit as st
from datetime import date, datetime, timedelta

##### FIREBASE INFO ---------------------------

import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    })
    firebase_admin.initialize_app(cred)

db = firestore.client()

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MEALS = ["Breakfast", "Lunch", "Dinner", "SNACKS"]

def create_empty_weekly_plan():
    return {day: {meal: [] for meal in MEALS} for day in DAYS}

def load_data():
    fridge_doc = db.collection("fridge").document("current").get()
    weekly_plan_doc = db.collection("weekly_plan").document("current").get()

    fridge = fridge_doc.to_dict() if fridge_doc.exists else {}
    weekly_plan = weekly_plan_doc.to_dict() if weekly_plan_doc.exists else create_empty_weekly_plan()
    return fridge, weekly_plan

def save_data():
    db.collection("fridge").document("current").set(st.session_state.fridge)
    db.collection("weekly_plan").document("current").set(st.session_state.weekly_plan)


##### -----------------------------------------



DATA_FILE = "fridge_data.json"

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MEALS = ["Breakfast", "Lunch", "Dinner", "SNACKS"]

CATEGORIES = [
    "🥩 meats & poultry 🐔",
    "🐟 seafood 🦐",
    "🥚 eggs & dairy 🥛",
    "☕️ beverages 🍵",
    "🍎 fruits & veggies 🥕",
    "🍚 dried goods",
    "🍝 pre-made foods/leftovers 🥡",
    "🧊 frozen/instant foods 🍽️",
    "🍧 sauces ",
    "🍿 snacks"
]

CATEGORY_EMOJIS = {
    "🥩 meats & poultry 🐔": "🥩🐔",
    "🐟 seafood 🦐": "🐟🦐",
    "🥚 eggs & dairy 🥛": "🥚🥛",
    "☕️ beverages 🍵": "☕️🍵",
    "🍎 fruits & veggies 🥕": "🍎🥕",
    "🍚 dried goods": "🍚",
    "🍝 pre-made foods/leftovers 🥡": "🍝🥡",
    "🧊 frozen/instant foods 🍽️": "🧊🍽️",
    "🍧 sauces ": "🍧",
    "🍿 snacks": "🍿"
}


def create_empty_weekly_plan():
    return {day: {meal: [] for meal in MEALS} for day in DAYS}


if "fridge" not in st.session_state or "weekly_plan" not in st.session_state:
    fridge, weekly_plan = load_data()
    st.session_state.fridge = fridge
    st.session_state.weekly_plan = weekly_plan

if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []


fridge_doc = db.collection("fridge").document("current").get()
print(fridge_doc.exists)


# WOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOW
# HELPERS
# WOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOW

def add_to_fridge(name, quantity, unit, category, staple, low_threshold=None, has_expiry=False, expiry_days=None):
    name = name.lower()
    if name in st.session_state.fridge:
        st.session_state.fridge[name]["quantity"] += quantity
    else:
        st.session_state.fridge[name] = {
            "quantity": float(quantity),
            "unit": unit,
            "category": category,
            "staple": staple,
            "low_threshold": float(low_threshold) if staple and low_threshold else None, 
            "has_expiry": has_expiry,
            "expiry_days": float(expiry_days) if has_expiry and expiry_days else None,
            "date_added": str(date.today()) if has_expiry else None,
        }

def remove_from_fridge(name, quantity):
    name = name.lower()
    if name in st.session_state.fridge:
        st.session_state.fridge[name]["quantity"] -= quantity
        if st.session_state.fridge[name]["quantity"] <= 0:
            del st.session_state.fridge[name]

def use_ingredients(ingredients):
    # Save previous state for undo
    undo_snapshot = {}
    for item in ingredients:
        name = item["name"]
        if name in st.session_state.fridge:
            undo_snapshot[name] = st.session_state.fridge[name]["quantity"]
    if undo_snapshot:
        st.session_state.undo_stack.append(undo_snapshot)
    
    # Deduct from fridge
    for item in ingredients:
        remove_from_fridge(item["name"], item["quantity"])

def cook_entire_meal(dishes):
    for dish in dishes:
        if not dish.get("eaten", False):
            use_ingredients(dish["ingredients"])
            dish["eaten"] = True

def build_grocery_list():
    needed = {}

    for day in st.session_state.weekly_plan.values():
        for meal in day.values():
            for dish in meal:
                if dish.get("ate_out", False):
                    continue
                for ing in dish.get("ingredients", []):
                    name = ing["name"]
                    qty = ing["quantity"]

                    if name not in st.session_state.fridge:
                        needed[name] = needed.get(name, 0) + qty

    return needed

def get_expiry_status(item_info):
    if not item_info.get("has_expiry"):
        return None

    try:
        added_str = item_info.get("date_added")
        days = item_info.get("expiry_days")

        # backward compatibility for old data
        if days is None and item_info.get("expiry_weeks") is not None:
            days = int(float(item_info.get("expiry_weeks")) * 7)

        if not added_str or not days:
            return None

        added = datetime.strptime(added_str, "%Y-%m-%d").date()
        expiry_date = added + timedelta(days=days)
        days_left = (expiry_date - date.today()).days

        if days_left < 0:
            return ("expired", days_left)
        elif days_left <= 3:
            return ("soon", days_left)
        else:
            return ("ok", days_left)
    except Exception:
        return None
# WOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOW
# UI
# WOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOW

st.set_page_config(page_title="Inside My Inventory", layout="wide")
st.title("🥕 Inside My Inventory")

main_tabs = st.tabs(["🧊 Inventory", "🍽 Meal Plan", "📋 Summary"])

# FRIDGE TAB
with main_tabs[0]:

    st.subheader("⚠️ Low Staples Summary")
    low_items = [
        (name, info["quantity"], info["unit"], info["category"])
        for name, info in st.session_state.fridge.items()
        if info["staple"] and info["low_threshold"] is not None and info["quantity"] <= info["low_threshold"]
    ]
    if low_items:
        for name, qty, unit, cat in low_items:
            emoji = CATEGORY_EMOJIS.get(cat, "❓")
            st.write(f"{emoji} **{name}** — {qty:.2f} {unit}")
    else:
        st.write("All staples are sufficiently stocked ✅")

    st.header("Add Grocery Haul")
    col1, col2 = st.columns(2)
    with col1:
        item_name = st.text_input("Ingredient name")
        quantity = st.number_input("Quantity", min_value=0.1, step=0.1, format="%.2f")
        unit = st.text_input("Unit (e.g. cups, sticks, lb, count)")
    with col2:
        category = st.selectbox("Category", CATEGORIES)
        staple = st.checkbox("Staple item")
        low_threshold = None
        if staple:
            low_threshold = st.number_input("Low threshold (alert when below this)", min_value=0.0, step=0.1, format="%.2f")
        has_expiry = st.checkbox("Track expiration")

        expiry_days = None
        if has_expiry:
            expiry_days = st.number_input(
                "Lasts how many days?",
                min_value=1,
                step=1,
            )

    if st.button("Add to Fridge"):
        if item_name and unit:
            add_to_fridge(item_name, quantity, unit, category, staple, low_threshold, has_expiry, expiry_days)
            st.info("Added to inventory...")
            save_data()
            st.rerun()

    st.divider()
    st.header("Current Inventory")
    for cat in CATEGORIES:
        items_in_cat = {k: v for k, v in st.session_state.fridge.items() if v["category"] == cat}
        if items_in_cat:
            with st.expander(cat.title(), expanded=False):
                for item, info in items_in_cat.items():
                    col1, col2 = st.columns([6,1])
                    low_warning = ""
                    # --- expiry warning ---
                    expiry_warning = ""
                    status_exp = get_expiry_status(info)

                    if status_exp:
                        state, days_left = status_exp
                        if state == "expired":
                            expiry_warning = " 🚨 EXPIRED"
                        elif state == "soon":
                            expiry_warning = f" ⚠️ use soon ({days_left}d)"
                    if info["staple"] and info["low_threshold"] is not None:
                        if info["quantity"] <= info["low_threshold"]:
                            low_warning = " ⚠️⏳⚠️"
                    col1.write(f"**{item}** — {info['quantity']:.2f} {info['unit']}{low_warning}{expiry_warning}")
                    if col2.button("❌", key=f"delete_{item}"):
                        del st.session_state.fridge[item]
                        save_data()
                        st.rerun()

    st.divider()
    st.subheader("Manually Reduce Item")
    if st.session_state.fridge:
        selected_item = st.selectbox("Select item", list(st.session_state.fridge.keys()))
        max_qty = st.session_state.fridge[selected_item]["quantity"]
        reduce_qty = st.number_input("Reduce by", min_value=0.1, max_value=float(max_qty), step=0.1, format="%.2f")
        if st.button("Remove Quantity"):
            remove_from_fridge(selected_item, reduce_qty)
            save_data()
            st.rerun()

    st.divider()
    if st.session_state.undo_stack:
        if st.button("↩️ Undo Last Dish"):
            last = st.session_state.undo_stack.pop()
            for name, qty in last.items():
                st.session_state.fridge[name]["quantity"] = qty
            save_data()
            st.success("Last dish undone!")
            st.rerun()


# MEAL PLAN TAB
with main_tabs[1]:

    if st.button("🔄 Reset Weekly Meal Plan"):
        st.session_state.weekly_plan = create_empty_weekly_plan()
        save_data()
        st.rerun()

    day_tabs = st.tabs(DAYS)
    fridge_items = list(st.session_state.fridge.keys())
    placeholder = "Select ingredient..."  # dropdown placeholder

    for idx, day in enumerate(DAYS):
        with day_tabs[idx]:
            for meal in MEALS:
                st.subheader(meal)

                col_dish_buttons = st.columns(3)

                # ----------------- Add Dish -----------------
                with col_dish_buttons[0]:
                    toggle_key = f"{day}_{meal}_add_dish_toggle"
                    input_key = f"{day}_{meal}_add_dish_name"

                    if toggle_key not in st.session_state:
                        st.session_state[toggle_key] = False

                    # button to open form
                    if not st.session_state[toggle_key]:
                        if st.button("➕ Add Dish", key=f"{day}_{meal}_add_dish_btn"):
                            st.session_state[toggle_key] = True
                            st.rerun()

                    # form appears
                    if st.session_state[toggle_key]:
                        dish_name = st.text_input(
                            "Dish name",
                            key=input_key,
                            placeholder="Enter dish name..."
                        )

                        col_c, col_x = st.columns(2)

                        with col_c:
                            if st.button("Confirm", key=f"{day}_{meal}_confirm_add_dish"):
                                if dish_name:
                                    st.session_state.weekly_plan[day][meal] = [
                                        dish for dish in st.session_state.weekly_plan[day][meal]
                                        if not dish.get("ate_out", False) and dish["name"] != "Skipped Meal"
                                    ]

                                    st.session_state.weekly_plan[day][meal].append({
                                        "name": dish_name,
                                        "ingredients": [],
                                        "cooked": False,
                                        "eaten": False, 
                                        "is_drink": False
                                    })

                                    save_data()

                                st.session_state[toggle_key] = False
                                if input_key in st.session_state:
                                    del st.session_state[input_key]
                                st.rerun()

                        with col_x:
                            if st.button("Cancel", key=f"{day}_{meal}_cancel_add_dish"):
                                st.session_state[toggle_key] = False
                                if input_key in st.session_state:
                                    del st.session_state[input_key]
                                st.rerun()

                # ----------------- Ate Out -----------------
                with col_dish_buttons[1]:
                    toggle_key = f"{day}_{meal}_ate_out_toggle"
                    input_key = f"{day}_{meal}_ate_out_name"

                    if toggle_key not in st.session_state:
                        st.session_state[toggle_key] = False

                    if not st.session_state[toggle_key]:
                        if st.button("🍽 Ate Out", key=f"{day}_{meal}_ate_out_btn"):
                            st.session_state[toggle_key] = True
                            st.rerun()

                    if st.session_state[toggle_key]:
                        restaurant_name = st.text_input(
                            "Where did you eat?",
                            key=input_key,
                            placeholder="Enter restaurant or cafe name..."
                        )

                        col_confirm, col_cancel = st.columns(2)

                        with col_confirm:
                            if st.button("Confirm", key=f"{day}_{meal}_confirm_ate_out"):
                                st.session_state.weekly_plan[day][meal] = []
                                st.session_state.weekly_plan[day][meal].append({
                                    "name": restaurant_name if restaurant_name else "Ate Out",
                                    "ingredients": [],
                                    "cooked": True,
                                    "eaten": True,
                                    "ate_out": True
                                })
                                save_data()

                                st.session_state[toggle_key] = False
                                if input_key in st.session_state:
                                    del st.session_state[input_key]

                                st.success("Meal marked as Ate Out ✅")
                                st.rerun()

                        with col_cancel:
                            if st.button("Cancel", key=f"{day}_{meal}_cancel_ate_out"):
                                st.session_state[toggle_key] = False
                                if input_key in st.session_state:
                                    del st.session_state[input_key]
                                st.rerun()

                # ----------------- Skipped Meal -----------------
                with col_dish_buttons[2]:
                    if st.button("⏭ Skipped Meal", key=f"{day}_{meal}_skipped_meal"):
                        # Remove all dishes and Ate Out
                        st.session_state.weekly_plan[day][meal] = []
                        # Add Skipped Meal entry
                        st.session_state.weekly_plan[day][meal].append({
                            "name": "Skipped Meal",
                            "ingredients": [],
                            "cooked": True,
                            "eaten": True
                        })
                        save_data()
                        st.success(f"{meal} marked as Skipped ✅")
                        st.rerun()

                # ----------------- Display Planned Dishes -----------------
                st.text("Planned Dishes:")
                dishes = st.session_state.weekly_plan[day][meal]

                # Hide "Consume Entire Meal" button if Ate Out / Skipped Meal
                if dishes and all(not d.get("ate_out", False) and d["name"] != "Skipped Meal" for d in dishes):
                    total_ingredients = sum(len(d["ingredients"]) for d in dishes)
                    if total_ingredients > 0:
                        if st.button(f"🔥 Consume Entire {meal}", key=f"{day}_{meal}_cook_all"):
                            cook_entire_meal(dishes)
                            save_data()
                            st.success(f"{meal} cooked!")
                            st.rerun()
                    else:
                        st.warning("⚠️ Cannot consume entire meal — no ingredients have been added yet!")

                for dish_index, dish in enumerate(dishes):
                    status = "✅" if dish.get("eaten", False) else ""
                    emoji = "🍹" if dish.get("is_drink", False) else "🍽"

                    with st.expander(f"{emoji} {dish['name']} {status}", expanded=False):
                        drink_toggle_key = f"{day}_{meal}_{dish_index}_is_drink"

                        is_drink_val = st.toggle(
                            "Mark as drink 🧋",
                            value=dish.get("is_drink", False),
                            key=drink_toggle_key
                        )

                        # Only update + rerun if it actually changed
                        if is_drink_val != dish.get("is_drink", False):
                            dish["is_drink"] = is_drink_val
                            save_data()
                            st.rerun()
                        # ----------------- Ingredient Inputs -----------------
                        if not dish.get("ate_out", False) and dish["name"] != "Skipped Meal":
                            col1, col2 = st.columns(2)
                            with col1:
                                options = [placeholder] + [
                                    f"{item} ({st.session_state.fridge[item]['unit']})"
                                    for item in fridge_items
                                ]
                                select_key = f"{day}_{meal}_{dish_index}_ing_name"

                                ing_name = st.selectbox(
                                    "Ingredient",
                                    options=options,
                                    index=options.index(placeholder),
                                    key=select_key
                                )
                            with col2:
                                qty_key = f"{day}_{meal}_{dish_index}_ing_qty"

                                ing_qty = st.number_input(
                                    "Quantity Used",
                                    min_value=0.1,
                                    step=0.1,
                                    format="%.2f",
                                    key=qty_key
                                )

                            # Add ingredient
                            if st.button("Add Ingredient", key=f"{day}_{meal}_{dish_index}_add_ing"):

                                if ing_name == placeholder:
                                    st.warning("Please select a valid ingredient from the fridge!")

                                else:
                                    ing_clean = ing_name.split(" (")[0].lower()

                                    if ing_clean not in st.session_state.fridge:
                                        st.error(f"'{ing_clean}' does not exist in the fridge!")

                                    # ✅ NEW: duplicate guard
                                    elif any(ing["name"] == ing_clean for ing in dish["ingredients"]):
                                        st.warning(f"'{ing_clean}' is already in this dish!")

                                    else:
                                        dish["ingredients"].append({
                                            "name": ing_clean,
                                            "quantity": ing_qty
                                        })

                                        # ✅ reset inputs
                                        value=0.1

                                        save_data()
                                        st.rerun()

                            # Show ingredients
                            ingredients = dish.get("ingredients", [])
                            for ing_index, ing in enumerate(ingredients):
                                col_ing1, col_ing2 = st.columns([6, 1])
                                unit = st.session_state.fridge.get(ing["name"], {}).get("unit", "")

                                col_ing1.write(f"{ing['quantity']:.2f} {ing['name']} {unit} ")

                                if col_ing2.button("Remove", key=f"{day}_{meal}_{dish_index}_del_ing_{ing_index}"):
                                    dish["ingredients"].pop(ing_index)
                                    save_data()
                                    st.rerun()

                            # Eat this dish
                            if not dish.get("ate_out", False):
                                if st.button("Eat This Dish", key=f"{day}_{meal}_{dish_index}_cook"):
                                    if not dish.get("eaten", False):
                                        use_ingredients(dish["ingredients"])
                                        dish["eaten"] = True
                                        save_data()
                                        st.success("Inventory updated!")
                                        st.rerun()
                                    else:
                                        st.warning("This dish has already been eaten.")
                        else:
                            st.info("This dish is marked as Ate Out or Skipped — no fridge ingredients needed.")

                        # Delete dish
                        if st.button("Remove Dish", key=f"{day}_{meal}_{dish_index}_delete"):
                            dishes.pop(dish_index)
                            save_data()
                            st.rerun()


                st.divider()

# MEAL PLAN SUMMARY TAB

with main_tabs[2]: 
    st.header("Weekly Meal Plan Overview")

    for day in DAYS:
        st.subheader(day)
        for meal in MEALS:
            st.markdown(f"**{meal}**")
            dishes = st.session_state.weekly_plan.get(day, {}).get(meal, [])
            if not dishes:
                st.write("_No dishes planned_")
            for dish in dishes:
                status = "✅ Eaten" if dish.get("eaten", False) else "⏳ Not eaten"
                emoji = "🍹" if dish.get("is_drink", False) else "🍽"
                st.write(f"- {emoji} {dish['name']} ({status})")
        st.divider()
