from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
import re
from kivymd.toast import toast
from logic import Graph, Group, Bill
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import StringProperty,NumericProperty
from datetime import datetime
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineAvatarIconListItem
from kivymd.uix.selectioncontrol import MDCheckbox
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDDatePicker
from collections import defaultdict


# Firebase imports
import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase
cred = credentials.Certificate("melosplit-firebase.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://melosplit-default-rtdb.firebaseio.com/"
})

def add_user_to_firebase(email, name):
    at_sign = email.find('@')
    uid = email[:at_sign] ##
    ref = db.reference("/users/")
    ref.child(email).set({"{uid}": name})

# def get_user_groups_from_firebase(uid):
#     groups_ref = db.reference("/groups/")
#     groups = groups_ref.get()
#     user_groups = []
#     if groups:
#         for group_id, group_data in groups.items():
#             if uid in group_data.get("members", []):
#                 user_groups.append(group_data.get("name", "Unknown Group"))
#     return user_groups

def local_data():
    """saving data in offline mode, uploadin when got online"""
    pass 

def local_loggedin():
    """not logging in again in same device"""
    pass 

the_group = None  # Global variable to store the active Group instance

def save_group_to_firebase():
    """Save the current the_group instance to Firebase."""
    global the_group
    if not the_group:
        raise ValueError("The group is not initialized.")

    # Convert the nested defaultdict to a standard dictionary for saving
    edges_dict = {
        payer: dict(payees)
        for payer, payees in the_group.graph.edges.items()
    }

    # Save all group data back to Firebase
    group_ref = db.reference(f"groups/{the_group.name}")
    group_ref.update({
        "members": the_group.members or {},
        "edges": edges_dict or {},
        # "transactions": the_group.graph.transactions or [],
        "recurring_bills": the_group.graph.recurring_bills,
        "category_totals": dict(the_group.graph.category_totals),
    })


class LoginScreen(MDScreen):
    def login(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()
        
        # Convert email to a safe key
        # safe_email = re.sub(r'[.#$/\[\]]', '_', email)
        at_sign = email.find('@') ##
        safe_email = email[:at_sign]

        if not email or not password:
            self.show_error("Please fill in all fields.")
            return

        # Check Firebase for the user
        user_ref = db.reference(f"/users/{safe_email}")
        user_data = user_ref.get()

        if user_data and user_data.get("password") == password:
            App.get_running_app().user_email = email  ##
            App.get_running_app().user_uid = safe_email  # Store UID for future use
            App.get_running_app().root.current = "group_manager"
        else:
            self.show_error("Invalid email or password.")

    def show_error(self, message):
        dialog = MDDialog(title="Error", text=message, buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())])
        dialog.open()


class SignupScreen(MDScreen):
    def signup(self):
        email = self.ids.email_input.text.strip()
        password = self.ids.password_input.text.strip()

        # # Convert email to a safe key
        # safe_email = re.sub(r'[.#$/\[\]]', '_', email)
        at_sign = email.find('@') ##
        safe_email = email[:at_sign]

        if not email or not password:
            self.show_error("Please fill in all fields.")
            return

        # Check if user already exists
        user_ref = db.reference(f"/users/{safe_email}")
        if user_ref.get():
            self.show_error("User already exists. Please log in.")
            return

        # Save the new user
        user_ref.set({
            "email": email,
            "password": password,
        })

        App.get_running_app().user_email = email  ##
        App.get_running_app().user_uid = safe_email
        App.get_running_app().root.current = "group_manager"

    def show_error(self, message):
        dialog = MDDialog(title="Error", text=message, buttons=[MDFlatButton(text="OK", on_release=lambda x: dialog.dismiss())])
        dialog.open()


class GroupManagerScreen(Screen):
    def on_enter(self):
        """Load groups when the screen is displayed."""
        self.load_groups()

    def load_groups(self):
        """Load user groups dynamically into the group list."""
        user_uid = App.get_running_app().user_uid
        # print(type(user_uid))
        self.update_user_groups_in_firebase(user_uid)
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        groups = user_groups_ref.get() or {}

        group_list = self.ids.group_list
        group_list.clear_widgets()
        for group_name in groups:
            # Properly handle the button instance passed by on_release
            group_list.add_widget(
                MDRaisedButton(
                    text=group_name,
                    on_release=lambda btn, group=group_name: self.go_to_group_screen(group),
                )
            )

    def update_user_groups_in_firebase(self, member_uid):
        """
        Find all groups that a specific member belongs to and update them
        in the Firebase path users/{member_uid}/groups.
        """
        groups_ref = db.reference("/groups")
        groups = groups_ref.get()  # Fetch all groups

        if not groups:
            return

        user_groups_path = f"/users/{member_uid}/groups"
        user_groups_ref = db.reference(user_groups_path)

        # Prepare a dictionary to update the user's groups
        user_groups = {}

        # Loop through all groups
        for group_name, group_data in groups.items():  # Use the key as the group name
            members = group_data.get("members", {})
            if member_uid in members:
                user_groups[group_name] = group_name  # Use the group key itself as the name

        # Update the user's group list in Firebase
        user_groups_ref.set(user_groups)


    def go_to_group_screen(self, group_name):
        """Navigate to the selected group's screen and initialize the_group."""
        global the_group

        # Fetch group data from Firebase
        group_data_ref = db.reference(f"groups/{group_name}")
        group_data = group_data_ref.get()

        if not group_data:
            toast(f"Group {group_name} not found!")
            return

        # Load edges (nested dictionary) from Firebase or use an empty structure if absent
        edges = group_data.get("edges", {})
        edges = defaultdict(lambda: defaultdict(float), {
            payer: defaultdict(float, payees)
            for payer, payees in edges.items()
        })

        # Initialize the global Group instance
        the_group = Group(
            name=group_name,
            members= group_data.get("members", {}),
            edges=edges,
            # transactions=list(group_data.get("transactions", {}).values()),
            recurring_bills=group_data.get("recurring_bills", []),
            category_totals=defaultdict(float, group_data.get("category_totals", {})),
        )

        App.get_running_app().group_name = group_name 
        # print(dict(the_group.graph.edges))
        self.manager.current = "group_screen"


class AddGroupScreen(Screen):
    def next_step(self):
        """Validate group name and number of members, then navigate to member input screen."""
        group_name = self.ids.group_name_input.text.strip()
        num_members = self.ids.num_members_input.text.strip()

        if not group_name:
            toast("Please enter a group name.")
            return
        if not num_members.isdigit() or int(num_members) <= 1:
            toast("Please enter a valid number of members.")
            return

        # Pass data to the next screen
        self.manager.get_screen("member_inputs_screen").setup_inputs(
            group_name, int(num_members)
        )

        global the_group
        the_group = Group(group_name)
        self.manager.current = "member_inputs_screen"


class MemberTemplate(MDBoxLayout):
    pass


class MemberInputsScreen(Screen):
    def setup_inputs(self, group_name, num_members):
        """Prepare inputs for member names and emails."""
        self.group_name = group_name  # Store the group name
        member_list = self.ids.member_inputs_list
        member_list.clear_widgets()  # Clear existing widgets

        # Add input fields for each member
        for _ in range(num_members):
            member_widget = MemberTemplate()  # Create a new instance of MemberTemplate
            member_list.add_widget(member_widget)
            if _ == 0:  # For the first member
                member_widget.ids.member_name.text = App.get_running_app().user_uid ##
                member_widget.ids.member_email.text = App.get_running_app().user_email ##


    def submit_group(self):
        """Add group to Firebase, validate emails, and initialize the graph."""
        group_name = self.group_name
        members = []

        # Collect member details from inputs
        for child in self.ids.member_inputs_list.children:
            name = child.ids.member_name.text.strip()
            email = child.ids.member_email.text.strip()

            if name:
                if email:
                    # Validate email and fetch UID
                    member_uid = email.split('@')[0] ##
                    # user_ref = db.reference(f"/users/{member_uid}")
                    # user_data = user_ref.get()
                    # if user_data:
                    members.append({"uid": member_uid, "name": name})  ##
                    # else:
                    #     toast(f"User with email {email} does not exist.")
                    #     return
                else:
                    members.append({"uid": None, "name": name})

        if len(members) < 2:
            toast("A group must have 2 members at least.")  ##
            return

        global the_group
        for member in members:
            the_group.add_member(member["name"])

        # Save the group to Firebase
        user_uid = App.get_running_app().user_uid
        group_ref = db.reference(f"groups/{group_name}")
        members_data = {
            "members": {m["uid"] or m["name"]: m["name"] for m in members},
        }
        group_ref.set(members_data)

        # Add the group to the user's groups;
        user_groups_ref = db.reference(f"users/{user_uid}/groups")
        user_groups_ref.update({group_name: 0})  ##
        # and to the registered members' groups:
        for member in members:
            if member['uid']:
                member_ref = db.reference(f"/users/{member['uid']}")
                member_data = member_ref.get()
                if member_data:
                    member_groups_ref = db.reference(f"/users/{member['uid']}/groups")
                    member_groups_ref.update({group_name: 0})


        # current_users_list_ref = db.reference(f"users")
        # for member in members:
        #     if member["uid"]:
        #         for uid in dict(current_users_list_ref):
        #             if member["uid"] == uid:
        #                 member_groups_ref = db.reference(f"users/{member}/groups")
        #                 member_groups_ref.update({group_name: 0})

        # # Initialize the group graph
        # the_group = Group(group_name, members_data)  ##
        # for member in members:
        #     member_id = member["uid"] or member["name"]  # Use UID if available, otherwise use the name
        #     if member_id:
        #         the_group.graph.add_transaction(member_id, user_uid, 0)  ## This stuff commented.

        toast(f"Group '{group_name}' created.")
        self.manager.current = "group_manager"


class GroupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.categorized_view = False  # Track current view mode

    def on_enter(self):
        """Set group title and load transaction history when entering the screen."""
        group_name = App.get_running_app().group_name
        self.ids.group_title.text = f"Group: {group_name}"
        self.show_normal_transactions()

    def toggle_transaction_view(self):
        """Switch between categorized and normal transaction view."""
        if self.categorized_view:
            self.show_normal_transactions()
            self.ids.toggle_view_button.text = "Show Categorized"
        else:
            self.categorized_transactions()
            self.ids.toggle_view_button.text = "Show All"
        self.categorized_view = not self.categorized_view

    def show_normal_transactions(self):
        """Display all transactions without categorization."""
        group_name = App.get_running_app().group_name
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()

        for transaction in reversed(list(transactions.values())):
            transactions_history.add_widget(
                MDLabel(
                    text=f"{transaction.get('payer')} paid {transaction.get('amount')} USD for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                    font_size=dp(14),
                    size_hint_y=None,
                    height=dp(30),
                )
            )


    def categorized_transactions(self):
        """Fetch and display categorized transactions."""
        group_name = App.get_running_app().group_name
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        # Categorize transactions
        categorized = {}
        for transaction_id, transaction in transactions.items():
            category = transaction.get("category", "Uncategorized")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(transaction)

        # Update UI
        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()

        for category, transactions in categorized.items():
            # Add category header
            transactions_history.add_widget(
                MDLabel(
                    text=f"[b]{category}[/b]",
                    markup=True,
                    font_style="H6",
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            # Add transactions under the category
            for transaction in reversed(transactions):
                transactions_history.add_widget(
                    MDLabel(
                        text=f"{transaction.get('payer')} paid {transaction.get('amount')} USD for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                        font_size=dp(14),
                        size_hint_y=None,
                        height=dp(30),
                    )
                )

    def open_date_picker(self, target):
        """Open date picker for start or end date."""
        date_picker = MDDatePicker()
        date_picker.bind(on_save=lambda instance, value, _: self.set_date(value, target))
        date_picker.open()

    def set_date(self, date, target):
        """Set the selected start or end date."""
        if target == "start":
            self.start_date = date
            toast(f"Start date set to {date}")
        elif target == "end":
            self.end_date = date
            toast(f"End date set to {date}")

    def filter_transactions_by_timeline(self):
        """Filter transactions based on the selected timeline."""
        if not hasattr(self, "start_date") or not hasattr(self, "end_date"):
            toast("Please select both start and end dates.")
            return

        group_name = App.get_running_app().group_name
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        filtered = []
        for transaction in transactions.values():
            try:
                transaction_date = datetime.strptime(transaction.get("date"), "%Y-%m-%d %H:%M:%S").date()
                if self.start_date <= transaction_date <= self.end_date:
                    filtered.append(transaction)
            except ValueError as e:
                toast(f"Invalid date format in transaction: {e}")
                continue

        # Display filtered transactions
        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()
        for transaction in filtered:
            transactions_history.add_widget(
                MDLabel(
                    text=f"{transaction.get('payer')} paid {transaction.get('amount')} USD for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                    font_size=dp(14),
                    size_hint_y=None,
                    height=dp(30),
                )
            )

    def open_sort_menu(self):
        """Open a menu for sorting transactions."""
        menu_items = [
            {"text": "By Date", "on_release": lambda x="date": self.sort_transactions(x)},
            {"text": "By Amount", "on_release": lambda x="amount": self.sort_transactions(x)},
        ]
        self.sort_menu = MDDropdownMenu(caller=self.ids.toggle_view_button, items=menu_items, width_mult=4)
        self.sort_menu.open()

    def sort_transactions(self, criterion):
        """Sort transactions by the selected criterion."""
        group_name = App.get_running_app().group_name
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        # Sort transactions
        if criterion == "date":
            sorted_transactions = sorted(
                transactions.values(),
                key=lambda x: datetime.strptime(x.get("date"), "%Y-%m-%d %H:%M:%S"),
            )
        elif criterion == "amount":
            sorted_transactions = sorted(transactions.values(), key=lambda x: float(x.get("amount", 0)))

        # Update UI
        transactions_history = self.ids.transactions_history
        transactions_history.clear_widgets()
        for transaction in reversed(sorted_transactions):
            transactions_history.add_widget(
                MDLabel(
                    text=f"{transaction.get('payer')} paid {transaction.get('amount')} USD for {transaction.get('description', 'No description')} on {transaction.get('date')}",
                    font_size=dp(14),
                    size_hint_y=None,
                    height=dp(30),
                )
            )

        self.sort_menu.dismiss()

    def members_summary(self):
        pass

    def add_expences(self):
        pass

    def settle_ups(Self):
        pass


class TransactionHistoryWidget(MDBoxLayout):
    payer = StringProperty()
    participants = StringProperty()
    amount = StringProperty()
    description = StringProperty()
    date = StringProperty()


class MemberSummaryScreen(Screen):
    def on_enter(self):
        """Populate the screen with member data when the screen is entered."""
        self.populate_member_summary()

    def populate_member_summary(self):
        """Get the group summary and display the member balances."""
        # Get the group summary
        # group_name = App.get_running_app().group_name
        # group = db.reference(f"groups/{group_name}")

        global the_group
        summary = the_group.get_summary()
        balances = the_group.get_balances()

        # Clear existing content
        self.ids.member_list.clear_widgets()

        # Add each member's information
        for member, balance in balances.items():
            member_summary = f"{member}: Net Balance: {balance:.2f}"
            contribution = summary["per_member_contributions"].get(member, 0)
            member_summary += f", Contribution: {contribution:.2f}"

            # Create a label for the member's data and add it to the list
            self.ids.member_list.add_widget(
                MDLabel(text=member_summary, theme_text_color="Secondary", size_hint_y=None, height="40dp")
            )

        # Display total expenses
        total_expenses = summary["total_expenses"]
        self.ids.total_expenses_label.text = f"Total Expenses: {total_expenses:.2f}"

        # Optional: Add category breakdown
        category_summary = summary["category_summary"]
        self.ids.category_summary_label.text = "Category Summary: " + ", ".join(
            [f"{category}: {amount:.2f}" for category, amount in category_summary.items()]
        )
        
    def go_back(self):
        """Navigate back to the GroupScreen."""
        self.manager.current = "group_screen"

    def add_expense(self):
        """Navigate to AddExpenseScreen."""
        self.manager.current = "add_expense_screen"

    def settle_up(self):
        """Navigate to SettleUpScreen."""
        self.manager.current = "settle_up_screen"


class AddExpenseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.split_type_items = [
            {"text": "Equally", "viewclass": "OneLineListItem", "on_release": lambda x="Equally": self.set_split_type(x)},
            {"text": "By Percentage", "viewclass": "OneLineListItem", "on_release": lambda x="By Percentage": self.set_split_type(x)},
            {"text": "By Shares", "viewclass": "OneLineListItem", "on_release": lambda x="By Shares": self.set_split_type(x)},
            {"text": "Custom", "viewclass": "OneLineListItem", "on_release": lambda x="Custom": self.set_split_type(x)},
        ]

        self.category_items = [
            {"text": "Food", "viewclass": "OneLineListItem", "on_release": lambda x="Food": self.set_category(x)},
            {"text": "Transport", "viewclass": "OneLineListItem", "on_release": lambda x="Transport": self.set_category(x)},
            {"text": "Utilities", "viewclass": "OneLineListItem", "on_release": lambda x="Utilities": self.set_category(x)},
            {"text": "Miscellaneous", "viewclass": "OneLineListItem", "on_release": lambda x="Miscellaneous": self.set_category(x)},
        ]

        self.split_type_menu = MDDropdownMenu(items=self.split_type_items, width_mult=4)
        self.category_menu = MDDropdownMenu(items=self.category_items, width_mult=4)

        self.participants_dialog = None  # To manage the participants dialog
        self.selected_participants = set()

    def open_split_type_menu(self, button):
        """Open split type menu safely."""
        if not self.split_type_menu.parent:
            self.split_type_menu.caller = button
            self.split_type_menu.open()

    def set_split_type(self, value):
        self.ids.split_type.text = value
        self.split_type_menu.dismiss()

    def open_split_type_menu(self, button):
        """Open split type menu safely."""
        if not self.split_type_menu.parent:
            self.split_type_menu.caller = button
            self.split_type_menu.open()

    def open_category_menu(self, button):
        """Open category menu safely."""
        if not self.category_menu.parent:
            self.category_menu.caller = button
            self.category_menu.open()


    def set_category(self, value):
        self.ids.category.text = value
        self.category_menu.dismiss()

    def open_participant_dialog(self):
        """Open participant dialog with input fields based on split type."""
        split_type = self.ids.split_type.text
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        if not group_data or "members" not in group_data:
            toast("No participants available in this group.")
            return

        participants = group_data["members"]
        self.dialog = ParticipantDialog(participants, self.update_selected_participants, split_type)
        self.dialog.open()


    def update_selected_participants(self, selected_participants):
        """Update the UI and internal state with selected participants and values."""
        self.selected_participants = selected_participants
        participant_text = ", ".join(
            f"{name} ({value})" for name, value in selected_participants.items()
        )
        self.ids.selected_participants_label.text = (
            f"Selected: {participant_text}" if participant_text else "None"
        )

    def add_expense(self):
        """Add expense using logic and save it to Firebase."""
        payer = self.ids.payer_name.text.strip()
        amount = self.ids.amount.text.strip()
        split_type = self.ids.split_type.text.strip()
        category = self.ids.category.text.strip()
        description = self.ids.description.text.strip()

        if not payer or not amount or not split_type or not category:
            self.ids.error_label.text = "All fields except description are required!"
            return

        if not self.selected_participants:
            self.ids.error_label.text = "At least one participant must be selected!"
            return

        # Convert amount to float
        try:
            amount = float(amount)
        except ValueError:
            self.ids.error_label.text = "Invalid amount!"
            return

        # Prepare custom splits or percentages for specific modes
        custom_splits = self.selected_participants

        if split_type == "By Shares" and sum(custom_splits.values()) <= 0:
            self.ids.error_label.text = "Total shares must be greater than zero!"
            return
        if split_type == "By Percentage" and abs(sum(custom_splits.values()) - 100) > 0.01:
            self.ids.error_label.text = "Total percentage must equal 100!"
            return
        if split_type == "Custom" and abs(sum(custom_splits.values()) - amount) > 0.01:
            self.ids.error_label.text = "Custom amounts must sum to the total amount!"
            return


        # Initialize or load the group graph
        global the_group
        group_name = App.get_running_app().group_name
        group_graph = the_group.graph

        # Add the bill to the graph
        group_graph.add_bill(
            Bill(
                payer=payer,
                amount=amount,
                participants=list(self.selected_participants),
                category=category,
            ),
            split_type=split_type,
            custom_splits=custom_splits,
        )
        print(f"\nA:\n{dict(group_graph.edges)}")
        print(f"\n\nB:\n{dict(group_graph.category_totals)}\n")
        print(the_group.members)

        save_group_to_firebase()

        # Save transaction to Firebase
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transaction_ref.push({
            "payer": payer,
            "participants": list(self.selected_participants),
            "amount": amount,
            "category": category,
            "split_type": split_type,
            "custom_splits": custom_splits,
            "description": description,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        # Clear inputs and provide feedback
        self.clear_inputs()
        toast("Expense added successfully.")
        self.manager.current = "group_screen"

    # def get_group_graph(self, group_name):
    #     """Retrieve or initialize the graph for a specific group."""
    #     group_ref = db.reference(f"groups/{group_name}/graph")
    #     group_graph = Graph()
    #     return group_graph

    def clear_inputs(self):
        """Clear all input fields."""
        self.ids.payer_name.text = ""
        self.ids.amount.text = ""
        self.ids.split_type.text = ""
        self.ids.category.text = ""
        self.ids.description.text = ""
        self.selected_participants.clear()

    def highlight_selected_participants(self):
        pass


from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import OneLineListItem, MDList
from kivy.uix.scrollview import ScrollView


class ParticipantDialog:
    def __init__(self, participants, on_submit, split_type="Equally"):
        """
        :param participants: List of participant names.
        :param on_submit: Callback function to handle selected participants.
        :param split_type: The split type (e.g., "Equally", "By Percentage", "By Shares", "Custom").
        """
        self.participants = participants
        self.split_type = split_type
        self.selected_participants = {}
        self.on_submit = on_submit

        # Create dialog content
        self.dialog_content = MDBoxLayout(orientation="vertical", spacing=10, size_hint_y=None)
        self.dialog_content.height = len(participants) * 60 + 20

        scroll = ScrollView()
        list_view = MDList()

        # Add participant inputs or checkboxes
        for name in participants:
            item = MDBoxLayout(orientation="horizontal", spacing=10, size_hint_y=None, height=60)

            if split_type == "Equally":
                # For "Equally", use checkboxes only
                checkbox = MDCheckbox(size_hint_x=0.1)
                checkbox.bind(active=lambda _, active, name=name: self.toggle_selection(active, name))
                item.add_widget(checkbox)
            else:
                # For other split types, use input fields only
                input_field = MDTextField(
                    hint_text=self.get_hint_text(),
                    size_hint_x=0.4,
                    halign="center",
                    pos_hint={"center_y": 0.5},  # Adjust alignment
                )
                item.add_widget(input_field)
                self.selected_participants[name] = {"selected": True, "value": input_field}

            label = MDLabel(text=name, size_hint_x=0.6 if split_type != "Equally" else 0.9)
            item.add_widget(label)

            list_view.add_widget(item)

        scroll.add_widget(list_view)
        self.dialog_content.add_widget(scroll)

        # Create dialog
        self.dialog = MDDialog(
            title=f"Select Participants ({split_type})",
            type="custom",
            content_cls=self.dialog_content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=self.dismiss),
                MDRaisedButton(text="OK", on_release=self.submit),
            ],
        )

    def open(self):
        """Open the dialog."""
        self.dialog.open()

    def dismiss(self, *args):
        """Close the dialog."""
        self.dialog.dismiss()

    def toggle_selection(self, active, name):
        """Toggle participant selection."""
        if self.split_type == "Equally":
            self.selected_participants[name] = {"selected": active}

    def submit(self, *args):
        """Submit selected participants and values."""
        if self.split_type == "Equally":
            selected = {name: 0 for name, field in self.selected_participants.items() if field["selected"]}
        else:
            selected = {
                name: float(field["value"].text) if field["value"].text.strip() else 0
                for name, field in self.selected_participants.items()
            }

        self.on_submit(selected)
        self.dismiss()

    def get_hint_text(self):
        """Return appropriate hint text based on the split type."""
        if self.split_type == "By Shares":
            return "Enter shares"
        elif self.split_type == "By Percentage":
            return "Enter %"
        elif self.split_type == "Custom":
            return "Enter amount"
        else:
            return ""


class AddRecurringBillScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.next_due_date = None
        self.selected_participants = {}

    def open_frequency_menu(self, instance):
        """Open dropdown for frequency selection."""
        menu_items = [
            {"text": "Weekly", "on_release": lambda x="Weekly": self.set_frequency(x)},
            {"text": "Monthly", "on_release": lambda x="Monthly": self.set_frequency(x)},
            {"text": "Yearly", "on_release": lambda x="Yearly": self.set_frequency(x)},
        ]
        self.frequency_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.frequency_menu.open()

    def set_frequency(self, frequency):
        """Set the selected frequency."""
        self.ids.frequency.text = frequency
        self.frequency_menu.dismiss()

    def open_split_type_menu(self, instance):
        """Open dropdown for split type selection."""
        menu_items = [
            {"text": "Equally", "on_release": lambda x="Equally": self.set_split_type(x)},
            {"text": "By Percentage", "on_release": lambda x="By Percentage": self.set_split_type(x)},
            {"text": "By Shares", "on_release": lambda x="By Shares": self.set_split_type(x)},
            {"text": "Custom", "on_release": lambda x="Custom": self.set_split_type(x)},
        ]
        self.split_type_menu = MDDropdownMenu(caller=instance, items=menu_items, width_mult=4)
        self.split_type_menu.open()

    def set_split_type(self, split_type):
        """Set the selected split type."""
        self.ids.split_type.text = split_type
        self.split_type_menu.dismiss()

    def open_participant_dialog(self):
        """Open participant selection dialog."""
        group_name = App.get_running_app().group_name
        group_ref = db.reference(f"groups/{group_name}")
        group_data = group_ref.get()

        if not group_data or "members" not in group_data:
            toast("No participants available in this group.")
            return

        participants = group_data["members"]
        self.dialog = ParticipantDialog(participants, self.update_selected_participants, self.ids.split_type.text)
        self.dialog.open()

    def update_selected_participants(self, selected_participants):
        """Update the UI and internal state with selected participants."""
        self.selected_participants = selected_participants
        participant_text = ", ".join(
            f"{name} ({value})" for name, value in selected_participants.items()
        )
        self.ids.selected_participants_label.text = (
            f"Selected: {participant_text}" if participant_text else "None"
        )

    def open_date_picker(self):
        """Open date picker for next due date."""
        date_picker = MDDatePicker()
        date_picker.bind(on_save=self.set_date)
        date_picker.open()

    def set_date(self, instance, value, _):
        """Set the selected date."""
        self.next_due_date = value
        self.ids.selected_date_label.text = f"Next Due Date: {value}"

    def add_recurring_bill(self):
        """Add recurring bill using logic and save it to Firebase."""
        payer = self.ids.payer_name.text.strip()
        amount = self.ids.amount.text.strip()
        split_type = self.ids.split_type.text.strip()
        frequency = self.ids.frequency.text.strip()
        description = self.ids.description.text.strip()

        if not payer or not amount or not split_type or not frequency or not self.next_due_date:
            toast("Please fill in all required fields.")
            return

        if not self.selected_participants:
            toast("At least one participant must be selected!")
            return

        # Convert amount to float
        try:
            amount = float(amount)
        except ValueError:
            toast("Invalid amount!")
            return

        # Initialize or load the group graph
        group_name = App.get_running_app().group_name
        group_graph = self.get_group_graph(group_name)

        # Add the recurring bill
        group_graph.add_recurring_bill(
            Bill(
                payer=payer,
                amount=amount,
                participants=list(self.selected_participants),
                category="",  # TODO: Add category logic if needed
                frequency=frequency,
                next_due_date=str(self.next_due_date),
            )
        )

        # Save the recurring bill to Firebase
        recurring_bills_ref = db.reference(f"groups/{group_name}/recurring_bills")
        recurring_bills_ref.push({
            "payer": payer,
            "amount": amount,
            "frequency": frequency,
            "next_due_date": str(self.next_due_date),
            "participants": self.selected_participants,
            "split_type": split_type,
            "description": description,
        })

        toast("Recurring bill added successfully.")
        self.manager.current = "group_screen"

    def get_group_graph(self, group_name):
        """Retrieve or initialize the graph for a specific group."""
        group_ref = db.reference(f"groups/{group_name}/graph")
        group_graph = Graph()
        return group_graph


class SettleUpScreen(Screen):
    def on_enter(self):
        """Generate and display the settle-up transactions when the screen is opened."""
        group_name = App.get_running_app().group_name
        group_graph = self.get_group_graph(group_name)  # Always fetch the latest graph data

        # Get simplified transactions
        simplified_transactions = group_graph.minimize_cash_flow()

        # Display the transactions
        settle_up_list = self.ids.settle_up_list
        settle_up_list.clear_widgets()

        if not simplified_transactions:
            settle_up_list.add_widget(
                MDLabel(
                    text="All debts are settled!",
                    halign="center",
                    font_style="H6",
                    size_hint_y=None,
                    height=dp(40),
                )
            )
        else:
            for payer, payee, amount in simplified_transactions:
                # Add transaction details and button inline
                item = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(10))
                item.add_widget(
                    MDLabel(
                        text=f"{payer} owes {payee} {amount:.2f} USD",
                        size_hint_x=0.7,
                    )
                )
                item.add_widget(
                    MDRaisedButton(
                        text="Settle Payment",
                        size_hint_x=0.3,
                        on_release=lambda p=payer, py=payee, a=amount: self.settle_payment(p, py, a),
                    )
                )
                settle_up_list.add_widget(item)

    def get_group_graph(self, group_name):
        """Build and return the graph dynamically from the transaction history in Firebase."""
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transactions = transaction_ref.get() or {}

        graph = Graph()

        # Recreate the graph using transaction history
        for transaction in transactions.values():
            payer = transaction.get("payer")
            amount = transaction.get("amount", 0)
            participants = transaction.get("participants", [])

            # Add each participant's share of the transaction to the graph
            for participant in participants:
                if payer and participant and participant != payer:
                    graph.add_transaction(payer, participant, amount / len(participants))

        return graph

    def settle_payment(self, payer, payee, amount):
        """Navigate to the settle payment screen with transaction details."""
        app = App.get_running_app()
        app.payer = payer
        app.payee = payee
        app.amount = amount
        app.root.current = "settle_payment_screen"


class SettlePaymentScreen(Screen):
    def confirm_payment(self):
        """Record the payment in the group graph and Firebase."""
        payer = self.ids.payer_name.text.strip()
        payee = self.ids.payee_name.text.strip()
        amount = self.ids.amount.text.strip()

        if not payer or not payee or not amount:
            toast("All fields are required!")
            return

        try:
            amount = float(amount)
        except ValueError:
            toast("Invalid amount!")
            return

        # Update group graph
        group_name = App.get_running_app().group_name
        group_graph = self.get_group_graph(group_name)
        group_graph.add_transaction(payer, payee, -amount)  # Negative amount to indicate payment

        # Record the payment in Firebase
        transaction_ref = db.reference(f"groups/{group_name}/transactions")
        transaction_ref.push({
            "payer": payer,
            "participants": [payee],
            "amount": -amount,
            "description": "Settle Payment",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        toast("Payment recorded successfully.")
        self.manager.current = "settle_up_screen"

    def get_group_graph(self, group_name):
        """Retrieve or initialize the graph for a specific group."""
        group_ref = db.reference(f"groups/{group_name}/graph")
        group_graph = Graph()
        return group_graph

    

class UserProfileScreen():
    """calculating and showing the user net balance in all their groups,the ability to change password and log out"""
    pass

class ParticipantListItem(OneLineAvatarIconListItem):
    uid = StringProperty("")

    def toggle_participant(self):
        """Toggle participant selection through AddExpenseScreen."""
        app = App.get_running_app()
        add_expense_screen = app.root.get_screen("add_expense_screen")
        add_expense_screen.toggle_participant(self.uid)

class ParticipantDialogContent(MDBoxLayout):
    """Content for the participant selection dialog."""
    pass

class MyScreenManager(ScreenManager):
    pass

class MeloSplit(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.payer = ""
        self.payee = ""
        self.amount = 0


    def build(self):
        self.theme_cls.primary_palette = "Blue"
        return MyScreenManager()

if __name__ == "__main__":
    MeloSplit().run()
