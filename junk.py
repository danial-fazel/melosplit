# members = []
# for _ in range(5):
#     text = input("Enter email adress: ")
#     at = text.find('@')
#     i = text[:at]
#     members.append(i)

# groups = ['add', 'dff', 'nvg', 'erh', 'oij', 'shd', {'m', 2,4}, (2, 4, 'df')]
# # groups = "asdfghjkloiuytrew"
# for item, jtem, ktem in groups:
#     print(f"{item=}\n{jtem=}\n{ktem=}\n.....")





# import firebase_admin
# from firebase_admin import credentials, db

# # Initialize Firebase
# cred = credentials.Certificate("melosplit-firebase.json")
# firebase_admin.initialize_app(cred, {
#     "databaseURL": "https://melosplit-default-rtdb.firebaseio.com/"
# })
# groups_ref = db.reference("/groups/")
# groups = groups_ref.get()
# print(groups.items())


from pprint import pprint
dickt = {[('Trip to Qazvin', {'members': {'ali': 'ali', 'asghar': 'asghar', 'mamad': 'mamad', 'melo': 'melo', 'nader': 'nader'}}), ('danelo', {'members': ['danial', ' emad']}), ('danial', {'members': ['dan.']}), ('malo', {'members': {'7QNszQJsH6gb7Yo5bJqKXEes8I82': 'mhdi'}, 'transactions': {'-OEySJ2mbDCJpbID89SU': {'amount': 330.0, 'category': 'food', 'date': '2024-12-25 19:05:17', 'participants': ['melo', ' danial', ' mehdi'], 'payer': 'melo', 'split_type': 'Split Type'}}}), ('maloo', {'members': {'dnialfa83@gmail_com': 'danial'}}), ('melo', {'members': {'mhdii': 'mhdii'}}), ('test', {'members': {'danialfzl841@gmail_com': 'dani', 'emad': 'emad', 'melo': 'melo', 'mhdi': 'mhdi'}, 'transactions': {'-OF-MGiaTpWC7R6FAhlj': {'amount': 230.0, 'category': 'Food', 'date': '2024-12-26 03:58:09', 'payer': 'dani', 'split_type': 'Equally'}, '-OF-MO8I7vJJ-QB-E6Hr': {'amount': 890.0, 'category': 'Food', 'date': '2024-12-26 03:58:39', 'payer': 'melo', 'split_type': 'Equally'}, '-OF6rwfzq-O1O32E5FI2': {'amount': 230.0, 'category': 'Food', 'date': '2024-12-27 14:58:12', 'description': '', 'participants': ['emad', 'melo'], 'payer': 'melo', 'split_type': 'Equally'}, '-OF7-lTrFbnlXZFIxJIh': {'amount': 250.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 2.0, 'melo': 1.0}, 'date': '2024-12-27 15:36:48', 'description': '', 'participants': ['danialfzl841@gmail_com', 'melo'], 'payer': 'melo', 'split_type': 'By Shares'}, '-OF703JAo6ogq9M9OF_q': {'amount': 400.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 70.0, 'mhdi': 30.0}, 'date': '2024-12-27 15:38:05', 'description': '', 'participants': ['danialfzl841@gmail_com', 'mhdi'], 'payer': 'melo', 'split_type': 'By Percentage'}, '-OF70JeiMBZQy0bC3SDc': {'amount': 300.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 0, 'emad': 30.0, 'melo': 0}, 'date': '2024-12-27 15:39:12', 'description': 'shity', 'participants': ['danialfzl841@gmail_com', 'emad', 'melo'], 'payer': 'emad', 'split_type': 'Equally'}, '-OF73pbeCRupZhOvaZoc': {'amount': 200.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 50.0, 'emad': 50.0, 'melo': 0, 'mhdi': 0}, 'date': '2024-12-27 15:54:34', 'description': '', 'participants': ['danialfzl841@gmail_com', 'emad', 'melo', 'mhdi'], 'payer': 'melo', 'split_type': 'By Percentage'}}})]}
print(type(dickt))