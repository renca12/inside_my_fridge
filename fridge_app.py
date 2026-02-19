import streamlit as st
import json
import os

##### FIREBASE INFO ---------------------------

import firebase_admin
from firebase_admin import credentials, firestore

if "firebase_app" not in st.session_state:
    cred = credentials.Certificate({
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"],
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    })

    st.session_state.firebase_app = firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()


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

# Load data from Firestore
def load_data():
    db = st.session_state.firebase_db
    
    fridge_doc = db.collection("fridge").document("current").get()
    weekly_plan_doc = db.collection("weekly_plan").document("current").get()
    
    fridge = fridge_doc.to_dict() if fridge_doc.exists else {}
    weekly_plan = weekly_plan_doc.to_dict() if weekly_plan_doc.exists else create_empty_weekly_plan()
    
    return fridge, weekly_plan

# Save data to Firestore
def save_data():
    db = st.session_state.firebase_db
    
    db.collection("fridge").document("current").set(st.session_state.fridge)
    db.collection("weekly_plan").document("current").set(st.session_state.weekly_plan)


if "fridge" not in st.session_state or "weekly_plan" not in st.session_state:
    fridge, weekly_plan = load_data()
    st.session_state.fridge = fridge
    st.session_state.weekly_plan = weekly_plan

if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []

# WOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOW
# HELPERS
# WOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOWOW

def add_to_fridge(name, quantity, unit, category, staple, low_threshold=None):
    name = name.lower()
    if name in st.session_state.fridge:
        st.session_state.fridge[name]["quantity"] += quantity
    else:
        st.session_state.fridge[name] = {
            "quantity": float(quantity),
            "unit": unit,
            "category": category,
            "staple": staple,
            "low_threshold": float(low_threshold) if staple and low_threshold else None
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

    if st.button("Add to Fridge"):
        if item_name and unit:
            add_to_fridge(item_name, quantity, unit, category, staple, low_threshold)
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
                    if info["staple"] and info["low_threshold"] is not None:
                        if info["quantity"] <= info["low_threshold"]:
                            low_warning = " ⚠️⏳⚠️"
                    col1.write(f"**{item}** — {info['quantity']:.2f} {info['unit']}{low_warning}")
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

                new_dish_name = st.text_input(f"Add Dish to {meal}", key=f"{day}_{meal}_new_dish")
                col_dish_buttons = st.columns(3)

                # ----------------- Add Dish -----------------
                with col_dish_buttons[0]:
                    if st.button("Add Dish", key=f"{day}_{meal}_add_dish"):
                        if new_dish_name:
                            # Remove Ate Out / Skipped Meal
                            st.session_state.weekly_plan[day][meal] = [
                                dish for dish in st.session_state.weekly_plan[day][meal]
                                if dish["name"] not in ["Ate Out", "Skipped Meal"]
                            ]
                            # Add new dish
                            st.session_state.weekly_plan[day][meal].append({
                                "name": new_dish_name,
                                "ingredients": [],
                                "cooked": False,
                                "eaten": False
                            })
                            save_data()
                            st.rerun()

                # ----------------- Ate Out -----------------
                with col_dish_buttons[1]:
                    if st.button("🍽 Ate Out", key=f"{day}_{meal}_ate_out_meal"):
                        # Remove all dishes and Skipped Meal
                        st.session_state.weekly_plan[day][meal] = []
                        # Add Ate Out entry
                        st.session_state.weekly_plan[day][meal].append({
                            "name": "Ate Out",
                            "ingredients": [],
                            "cooked": True,
                            "eaten": True
                        })
                        save_data()
                        st.success(f"{meal} marked as Ate Out ✅")
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
                if dishes and all(d["name"] not in ["Ate Out", "Skipped Meal"] for d in dishes):
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
                    with st.expander(f"🍽 {dish['name']} {status}", expanded=False):

                        # ----------------- Ingredient Inputs -----------------
                        if dish["name"] not in ["Ate Out", "Skipped Meal"]:
                            col1, col2 = st.columns(2)
                            with col1:
                                options = [placeholder] + fridge_items
                                ing_name = st.selectbox(
                                    "Ingredient",
                                    options=options,
                                    index=0,
                                    key=f"{day}_{meal}_{dish_index}_ing_name"
                                )
                            with col2:
                                ing_qty = st.number_input(
                                    "Quantity Used",
                                    min_value=0.1,
                                    step=0.1,
                                    format="%.2f",
                                    key=f"{day}_{meal}_{dish_index}_ing_qty"
                                )

                            # Add ingredient
                            if st.button("Add Ingredient", key=f"{day}_{meal}_{dish_index}_add_ing"):
                                if ing_name == placeholder:
                                    st.warning("Please select a valid ingredient from the fridge!")
                                elif ing_name.lower() not in st.session_state.fridge:
                                    st.error(f"'{ing_name}' does not exist in the fridge!")
                                else:
                                    dish["ingredients"].append({
                                        "name": ing_name.lower(),
                                        "quantity": ing_qty
                                    })
                                    save_data()
                                    st.success(f"Added {ing_qty:.2f} {st.session_state.fridge[ing_name.lower()]['unit']} of {ing_name} to {dish['name']}")
                                    st.rerun()

                            # Show ingredients
                            for ing in dish["ingredients"]:
                                st.write(f"- {ing['quantity']:.2f} {ing['name']}")

                            # Eat this dish
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
                st.write(f"- 🍽 {dish['name']} ({status})")
        st.divider()
