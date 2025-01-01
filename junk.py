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


# from pprint import pprint
# dickt = {[('Trip to Qazvin', {'members': {'ali': 'ali', 'asghar': 'asghar', 'mamad': 'mamad', 'melo': 'melo', 'nader': 'nader'}}), ('danelo', {'members': ['danial', ' emad']}), ('danial', {'members': ['dan.']}), ('malo', {'members': {'7QNszQJsH6gb7Yo5bJqKXEes8I82': 'mhdi'}, 'transactions': {'-OEySJ2mbDCJpbID89SU': {'amount': 330.0, 'category': 'food', 'date': '2024-12-25 19:05:17', 'participants': ['melo', ' danial', ' mehdi'], 'payer': 'melo', 'split_type': 'Split Type'}}}), ('maloo', {'members': {'dnialfa83@gmail_com': 'danial'}}), ('melo', {'members': {'mhdii': 'mhdii'}}), ('test', {'members': {'danialfzl841@gmail_com': 'dani', 'emad': 'emad', 'melo': 'melo', 'mhdi': 'mhdi'}, 'transactions': {'-OF-MGiaTpWC7R6FAhlj': {'amount': 230.0, 'category': 'Food', 'date': '2024-12-26 03:58:09', 'payer': 'dani', 'split_type': 'Equally'}, '-OF-MO8I7vJJ-QB-E6Hr': {'amount': 890.0, 'category': 'Food', 'date': '2024-12-26 03:58:39', 'payer': 'melo', 'split_type': 'Equally'}, '-OF6rwfzq-O1O32E5FI2': {'amount': 230.0, 'category': 'Food', 'date': '2024-12-27 14:58:12', 'description': '', 'participants': ['emad', 'melo'], 'payer': 'melo', 'split_type': 'Equally'}, '-OF7-lTrFbnlXZFIxJIh': {'amount': 250.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 2.0, 'melo': 1.0}, 'date': '2024-12-27 15:36:48', 'description': '', 'participants': ['danialfzl841@gmail_com', 'melo'], 'payer': 'melo', 'split_type': 'By Shares'}, '-OF703JAo6ogq9M9OF_q': {'amount': 400.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 70.0, 'mhdi': 30.0}, 'date': '2024-12-27 15:38:05', 'description': '', 'participants': ['danialfzl841@gmail_com', 'mhdi'], 'payer': 'melo', 'split_type': 'By Percentage'}, '-OF70JeiMBZQy0bC3SDc': {'amount': 300.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 0, 'emad': 30.0, 'melo': 0}, 'date': '2024-12-27 15:39:12', 'description': 'shity', 'participants': ['danialfzl841@gmail_com', 'emad', 'melo'], 'payer': 'emad', 'split_type': 'Equally'}, '-OF73pbeCRupZhOvaZoc': {'amount': 200.0, 'category': 'Food', 'custom_splits': {'danialfzl841@gmail_com': 50.0, 'emad': 50.0, 'melo': 0, 'mhdi': 0}, 'date': '2024-12-27 15:54:34', 'description': '', 'participants': ['danialfzl841@gmail_com', 'emad', 'melo', 'mhdi'], 'payer': 'melo', 'split_type': 'By Percentage'}}})]}
# print(type(dickt))



# # Firebase imports
# import firebase_admin
# from firebase_admin import credentials, db

# # Initialize Firebase
# cred = credentials.Certificate("melosplit-firebase.json")
# firebase_admin.initialize_app(cred, {
#     "databaseURL": "https://melosplit-default-rtdb.firebaseio.com/"
# })
# member_ref = db.reference(f"/users/xxzrqywg")
# member_data = member_ref.get()
# member_groups = member_data.get("groups")
# print(member_groups)

# from kivy_garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
# import matplotlib.pyplot as plt
# from kivy.app import App
# from kivy.uix.boxlayout import BoxLayout

# class TestApp(App):
#     def build(self):
#         layout = BoxLayout()
#         fig, ax = plt.subplots()
#         ax.plot([0, 1, 2], [0, 1, 4])
#         canvas = FigureCanvasKivyAgg(fig)
#         layout.add_widget(canvas)
#         return layout

# if __name__ == "__main__":
#     TestApp().run()




# old good one - safe for add expense

# class ParticipantDialog:
#     def __init__(self, participants, on_submit, split_type="Equally"):
#         """
#         :param participants: List of participant names.
#         :param on_submit: Callback function to handle selected participants.
#         :param split_type: The split type (e.g., "Equally", "By Percentage", "By Shares", "Custom").
#         """
#         self.participants = participants
#         self.split_type = split_type
#         self.selected_participants = {}
#         self.on_submit = on_submit

#         # Create dialog content
#         self.dialog_content = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
#         self.dialog_content.height = len(participants) * 60 + 20

#         scroll = ScrollView()
#         list_view = MDList()

#         # Add participant inputs or checkboxes
#         for uid, name in participants.items():
#             item = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=60)

#             if split_type == "Equally":
#                 # For "Equally", use checkboxes only
#                 checkbox = MDCheckbox(size_hint_x=0.1)
#                 checkbox.bind(active=lambda _, active, uid=uid: self.toggle_selection(active, uid))
#                 item.add_widget(checkbox)
#             else:
#                 # For other split types, use input fields only
#                 input_field = MDTextField(
#                     hint_text=self.get_hint_text(),
#                     size_hint_x=0.4,
#                     halign="center",
#                     pos_hint={"center_y": 0.5},  # Adjust alignment
#                 )
#                 item.add_widget(input_field)
#                 self.selected_participants[uid] = {"selected": True, "value": input_field}

#             label = MDLabel(text=name, size_hint_x=0.6 if split_type != "Equally" else 0.9)
#             item.add_widget(label)

#             list_view.add_widget(item)

#         scroll.add_widget(list_view)
#         self.dialog_content.add_widget(scroll)

#         # Create dialog
#         self.dialog = MDDialog(
#             title=f"Select Participants ({split_type})",
#             type="custom",
#             content_cls=self.dialog_content,
#             buttons=[
#                 MDFlatButton(text="CANCEL", on_release=self.dismiss),
#                 MDRaisedButton(text="OK", on_release=self.submit),
#             ],
#         )

#     def open(self):
#         """Open the dialog."""
#         self.dialog.open()

#     def dismiss(self, *args):
#         """Close the dialog."""
#         self.dialog.dismiss()

#     def toggle_selection(self, active, name):
#         """Toggle participant selection."""
#         if self.split_type == "Equally":
#             self.selected_participants[name] = {"selected": active}

#     def submit(self, *args):
#         """Submit selected participants and values."""
#         if self.split_type == "Equally":
#             selected = {name: 0 for name, field in self.selected_participants.items() if field["selected"]}
#         else:
#             selected = {
#                 name: float(field["value"].text) if field["value"].text.strip() else 0
#                 for name, field in self.selected_participants.items()
#             }

#         self.on_submit(selected)
#         self.dismiss()

#     def get_hint_text(self):
#         """Return appropriate hint text based on the split type."""
#         if self.split_type == "By Shares":
#             return "Enter shares"
#         elif self.split_type == "By Percentage":
#             return "Enter %"
#         elif self.split_type == "Custom":
#             return "Enter amount"
#         else:
#             return ""
