from pymongo import MongoClient
from pymongo.errors import ConfigurationError
import os
from django.shortcuts import render, redirect
from .models import User, Expense
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect

MONGO_URI = "mongodb+srv://jharshal500:macbookair@cluster0.o8kzf.mongodb.net/"
client = None
db = None

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect('home')
        else:
            messages.error(request, "Error creating account.")
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})



def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, "Logged in successfully.")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})



def logout(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')


def connect_to_db():
    global client, db
    try:
        client = MongoClient(MONGO_URI)
        db = client.get_database("splitwise_db")
        print("Connected to MongoDB successfully!")
    except ConfigurationError as e:
        print(f"Failed to connect to MongoDB: {e}")

connect_to_db()

def home(request):
    return render(request, 'home.html')

def add_user(request):
    if request.method == 'POST':
        name = request.POST['name']
        if db.users.find_one({"name": name}) is None:
            db.users.insert_one({"name": name, "balance": 0})
            messages.success(request, f"User '{name}' added successfully.")
        else:
            messages.warning(request, f"User '{name}' already exists.")
        return redirect('home')
    return render(request, 'add_user.html')

def add_expense(request):
    if request.method == 'POST':
        try:
            amount = float(request.POST['amount'])
            paid_by = request.POST['paid_by']
            split_type = request.POST['split_type']
            paid_by_user = db.users.find_one({"name": paid_by})
            if not paid_by_user:
                messages.error(request, f"User '{paid_by}' does not exist.")
                return redirect('add_expense')
            
            users = list(db.users.find())
            if split_type == 'equal':
                split_amount = amount / len(users)
                for user in users:
                    if user['name'] != paid_by:
                        db.users.update_one({"name": user['name']}, {"$inc": {"balance": -split_amount}})
                db.users.update_one({"name": paid_by}, {"$inc": {"balance": amount - split_amount}})

            elif split_type == 'custom':
                split_details = {}
                total_split = 0
                for user in users:
                    share = float(request.POST.get(user['name'], 0))
                    split_details[user['name']] = share
                    total_split += share

                if total_split != amount:
                    messages.error(request, "Error: Split details do not sum up to the total amount.")
                    return redirect('add_expense')

                for user_name, share in split_details.items():
                    db.users.update_one({"name": user_name}, {"$inc": {"balance": -share}})
                db.users.update_one({"name": paid_by}, {"$inc": {"balance": amount}})

            else:
                messages.error(request, "Invalid split type or missing split details.")
                return redirect('add_expense')

            db.expenses.insert_one({
                "amount": amount,
                "paid_by": paid_by,
                "split_type": split_type,
                "split_details": split_details if split_type == 'custom' else None,
            })
            messages.success(request, f"Expense of {amount} added successfully.")
            return redirect('home')
        except ValueError:
            messages.error(request, "Invalid input. Please enter numeric values where applicable.")
            return redirect('add_expense')
    users = db.users.find()
    return render(request, 'add_expense.html', {'users': users})

def show_balances(request):
    users = db.users.find()
    return render(request, 'show_balances.html', {'users': users})

def calculate_owe_details(request):
    owes = {}
    owed = {}
    users = db.users.find()

    for user in users:
        balance = user['balance']
        if balance < 0:
            owes[user['name']] = -balance
        elif balance > 0:
            owed[user['name']] = balance

    owe_details = []
    while owes and owed:
        debtor, debt_amount = owes.popitem()
        creditor, credit_amount = owed.popitem()

        amount = min(debt_amount, credit_amount)
        owe_details.append(f"{debtor} owes {creditor} {amount:.2f}")

        debt_amount -= amount
        credit_amount -= amount

        if debt_amount > 0:
            owes[debtor] = debt_amount
        if credit_amount > 0:
            owed[creditor] = credit_amount

    return render(request, 'calculate_owe_details.html', {'owe_details': owe_details})

def show_expense_details(request):
    expenses = db.expenses.find()
    return render(request, 'show_expense_details.html', {'expenses': expenses})

def show_totals_for_user(request):
    if request.method == 'POST':
        user_name = request.POST['user_name']
        user = db.users.find_one({"name": user_name})
        if not user:
            messages.error(request, f"User '{user_name}' does not exist.")
            return redirect('show_totals_for_user')

        totals = []
        user_balance = user['balance']

        for other_user in db.users.find():
            if other_user['name'] == user_name:
                continue
            
            other_balance = other_user['balance']
            if user_balance < 0 and other_balance > 0:
                amount_owed = min(-user_balance, other_balance)
                totals.append(f"{user_name} owes {other_user['name']} {amount_owed:.2f}")
            elif user_balance > 0 and other_balance < 0:
                amount_owed = min(user_balance, -other_balance)
                totals.append(f"{other_user['name']} owes {user_name} {amount_owed:.2f}")
            else:
                totals.append(f"{user_name} and {other_user['name']} are settled.")

        return render(request, 'show_totals_for_user.html', {'user': user_name, 'totals': totals})

    return render(request, 'show_totals_for_user.html')

def clear_all_dues(request):
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation', '').strip().lower()
        if confirmation == 'yes':
            # Clear all user balances
            db.users.update_many({}, {"$set": {"balance": 0}})
            
            # Clear all expenses
            db.expenses.delete_many({})
            
            messages.success(request, "All dues and expense details have been cleared.")
        else:
            messages.info(request, "Action canceled. No dues or expense details were cleared.")
        return redirect('home')
    
    return render(request, 'clear_all_dues.html')





# def add_user(request):
#     if request.method == 'POST':
#         name = request.POST['name']
#         if not User.objects.filter(name=name).exists():
#             User.objects.create(name=name)
#             messages.success(request, f"User '{name}' added successfully.")
#         else:
#             messages.warning(request, f"User '{name}' already exists.")
#         return redirect('home')
#     return render(request, 'add_user.html')

# def add_expense(request):
#     if request.method == 'POST':
#         amount = float(request.POST['amount'])
#         paid_by = request.POST['paid_by']
#         split_type = request.POST['split_type']
#         paid_by_user = User.objects.get(name=paid_by)
#         users = User.objects.all()

#         if split_type == 'equal':
#             split_amount = amount / users.count()
#             for user in users:
#                 if user != paid_by_user:
#                     user.balance -= split_amount
#                     user.save()
#             paid_by_user.balance += amount - split_amount
#             paid_by_user.save()
        
#         elif split_type == 'custom':
#             split_details = {}
#             total_split = 0
#             for user in users:
#                 share = float(request.POST.get(user.name, 0))
#                 split_details[user.name] = share
#                 total_split += share
#                 user.balance -= share
#                 user.save()

#             if total_split != amount:
#                 messages.error(request, "Error: Split details do not sum up to the total amount.")
#                 return redirect('add_expense')

#             paid_by_user.balance += amount
#             paid_by_user.save()
        
#         Expense.objects.create(amount=amount, paid_by=paid_by_user, split_type=split_type, split_details=split_details if split_type == 'custom' else None)
#         messages.success(request, f"Expense of {amount} added successfully.")
#         return redirect('home')
#     users = User.objects.all()
#     return render(request, 'add_expense.html', {'users': users})

# def show_balances(request):
#     users = User.objects.all()
#     return render(request, 'show_balances.html', {'users': users})

# def calculate_owe_details(request):
#     owes = {}
#     owed = {}
#     users = User.objects.all()

#     for user in users:
#         balance = user.balance
#         if balance < 0:
#             owes[user.name] = -balance
#         elif balance > 0:
#             owed[user.name] = balance

#     owe_details = []
#     while owes and owed:
#         debtor, debt_amount = owes.popitem()
#         creditor, credit_amount = owed.popitem()

#         amount = min(debt_amount, credit_amount)
#         owe_details.append(f"{debtor} owes {creditor} {amount:.2f}")

#         debt_amount -= amount
#         credit_amount -= amount

#         if debt_amount > 0:
#             owes[debtor] = debt_amount
#         if credit_amount > 0:
#             owed[creditor] = credit_amount

#     return render(request, 'calculate_owe_details.html', {'owe_details': owe_details})

# def show_expense_details(request):
#     expenses = Expense.objects.all()
#     return render(request, 'show_expense_details.html', {'expenses': expenses})

# def show_totals_for_user(request):
#     if request.method == 'POST':
#         user_name = request.POST['user_name']
#         user = User.objects.get(name=user_name)
#         users = User.objects.all()
#         totals = []

#         for other_user in users:
#             if other_user == user:
#                 continue
            
#             if user.balance < 0 and other_user.balance > 0:
#                 amount_owed = min(-user.balance, other_user.balance)
#                 totals.append(f"{user_name} owes {other_user.name} {amount_owed:.2f}")
#             elif user.balance > 0 and other_user.balance < 0:
#                 amount_owed = min(user.balance, -other_user.balance)
#                 totals.append(f"{other_user.name} owes {user_name} {amount_owed:.2f}")
#             else:
#                 totals.append(f"{user_name} and {other_user.name} are settled.")

#         return render(request, 'show_totals_for_user.html', {'user': user_name, 'totals': totals})

#     users = User.objects.all()
#     return render(request, 'show_totals_for_user.html', {'users': users})

# def clear_all_dues(request):
#     if request.method == 'POST':
#         confirmation = request.POST.get('confirmation', '').strip().lower()
#         if confirmation == 'yes':
#             User.objects.update(balance=0)
#             messages.success(request, "All dues have been cleared.")
#         else:
#             messages.info(request, "Action canceled. No dues were cleared.")
#         return redirect('home')
#     return render(request, 'clear_all_dues.html')
