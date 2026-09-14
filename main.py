expenses=[]
def add_expense(amount,category,description):
 expense={"amount":amount,"category":category,"description":description}
 expenses.append(expense)
 print(expenses)

add_expense(12, "Food", "lunch")
add_expense(8, "Transport", "bus")

def view_expense():
 for expense in expenses:
   print(expense)

def delete_expense(amount, category, description):
    expense = {"amount": amount, "category": category, "description": description}
    if expense in expenses:
        expenses.remove(expense)
        print(expense, "removed")
    else:
        print(expense, "NOT FOUND")
 
 
delete_expense(999,"Nonsense","fake")