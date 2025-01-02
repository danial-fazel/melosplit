from collections import defaultdict
from datetime import datetime, timedelta
import networkx as nx
import matplotlib.pyplot as plt
# from currency import convert_currency



# class Member:  ## 
#     def __init__(self, name):
#         self.name = name

class Group:
    def __init__(self, name, members={}, edges=defaultdict(lambda: defaultdict(float)), transactions=[], recurring_bills=[], category_totals=defaultdict(float)):  ##
        self.name = name
        self.members = members  # Members in the group
        self.graph = Graph(edges, transactions, recurring_bills, category_totals)  # Separate debt graph for this group

    def delete_group(self):
        """
        Clear all data associated with the group.
        """
        self.members = {}
        self.graph = None  # Clear the group's graph
        print(f"Group '{self.name}' has been deleted.")

    def remove_member(self, member):
        """
        Remove a member from the group and redistribute their balances.
        """
        if member not in list(self.members.keys()):
            raise ValueError(f"Member {self.members[member]} is not in the group.")

        balances = self.graph.calculate_balances()

        # Reassign debts
        remaining_members = [member_uid for member_uid , member_name in self.members.items() if member_uid != member]
        for payer, payees in self.graph.edges.items():
            if payer == member or member in payees:
                amount = payees.pop(member, 0)
                if remaining_members:
                    split_amount = amount / len(remaining_members)
                    for other_member in remaining_members:
                        if payer == member:
                            self.graph.add_transaction(member, other_member, split_amount)
                        elif other_member == member:
                            self.graph.add_transaction(other_member, payer, split_amount)

        # Remove the member
        del self.members[member]
        print(f"Member '{self.members[member]}' has been removed and debts redistributed.")

    def get_summary(self):
        """
        Generate a summary of the group's expenses and balances.
        Returns a dictionary with group totals, member contributions, and category breakdowns.
        """
        balances = self.graph.calculate_balances()
        category_summary = self.graph.get_category_summary()

        total_expenses = sum(category_summary.values())
        per_member_contributions = {member: -balances.get(member, 0) for member in list(self.members.values())}

        return {
            "total_expenses": total_expenses,
            "per_member_contributions": per_member_contributions,
            "category_summary": category_summary,
        }
    
    def get_category(self,category=None):###
         self.category = category
    def discript(self,discription=None):
        self.description = discription

    def add_member(self, member_name, member_uid=None):
        """Add a member to the group."""
        self.members[member_uid or member_name] = member_name

    def add_bill(self, bill, split_type="Equally", custom_splits=None):
        """
        Add a bill to the group's graph.
        """
        if bill.payer not in list(self.members.values()):
            raise ValueError(f"Payer {bill.payer} is not a member of this group.")
        for participant in bill.participants:
            if participant not in list(self.members.values()):
                raise ValueError(f"Participant {participant} is not a member of this group.")
        self.graph.add_bill(bill, split_type, custom_splits)

    def get_balances(self):
        """Get balances for the group."""
        return self.graph.calculate_balances()

    def get_transaction_history(self, filter_by=None):
        """Get transaction history for the group."""
        return self.graph.get_transaction_history(filter_by)

class Bill:
    def __init__(self, payer, amount, participants, frequency=None, next_due_date=None, category=None):
        self.payer = payer
        self.amount = amount
        self.participants = participants  # List of participant names
        self.frequency = frequency  # 'weekly', 'monthly', 'yearly', or None
        self.next_due_date = (
            datetime.strptime(next_due_date, "%Y-%m-%d") if next_due_date else None
        )
        self.category = category  # Category of the expense (e.g., 'Food', 'Travel')
        # self.currency = currency

    # def convert_amount(self, target_currency):
    #     """
    #     Convert the bill amount to the target currency.
    #     """
    #     if self.currency != target_currency:
    #         # from melosplit.currency import convert_currency
    #         self.amount = convert_currency(self.amount, self.currency, target_currency)
    #         self.currency = target_currency

    def update_next_due_date(self):
        """Update the next due date based on the frequency."""
        if not self.frequency:
            return  # One-time bill, no update needed

        if self.frequency == "weekly":
            self.next_due_date += timedelta(weeks=1)
        elif self.frequency == "monthly":
            self.next_due_date = self.next_due_date.replace(
                month=self.next_due_date.month % 12 + 1
            )
        elif self.frequency == "yearly":
            self.next_due_date = self.next_due_date.replace(year=self.next_due_date.year + 1)


class Graph:
    def __init__(self, edges=defaultdict(lambda: defaultdict(float)), transactions=[], recurring_bills=[], category_totals=defaultdict(float)):  ##
        self.edges = edges
        self.transactions = transactions  # Store all transaction history
        self.recurring_bills = recurring_bills  # Store recurring bills
        self.category_totals = category_totals  # Store totals for each category

    def add_recurring_bill(self, bill):
        """
        Add a recurring bill to the system.
        """
        if not bill.frequency or not bill.next_due_date:
            raise ValueError("Recurring bills must have a frequency and next_due_date.")
        self.recurring_bills.append(bill)

    def process_recurring_bills(self, current_date):
        """
        Check and process all recurring bills due by the given date.
        """
        current_date = datetime.strptime(current_date, "%Y-%m-%d")
        for bill in self.recurring_bills:
            if bill.next_due_date and bill.next_due_date <= current_date:
                # Add the bill to the graph as a one-time bill
                self.add_bill(Bill(bill.payer, bill.amount, bill.participants))
                # Update the next due date
                bill.update_next_due_date()

    def add_bill(self, bill, split_type="Equally", custom_splits=None):
        # bill.convert_amount(target_currency)  # Convert bill amount to target currency
        """
        Add a bill and log it in the transaction history.
        """
        transaction = {
            "payer": bill.payer,
            "amount": bill.amount,
            "participants": bill.participants,
            "category": bill.category,
            "split_type": split_type, 
            "custom_splits": custom_splits,  
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Add transaction date
            "description": "",
        }

        # Add the bill based on the split type
        if split_type == "Equally":
            split_amount = bill.amount / len(bill.participants)
            for participant in bill.participants:
                if participant != bill.payer:
                    self.add_transaction(bill.payer, participant, split_amount)

        elif split_type == "Custom":
            if not custom_splits:
                raise ValueError("Custom splits required for 'unequal' mode.")
            total_split = sum(custom_splits.values())
            if abs(total_split - bill.amount) > 0.01:
                raise ValueError("Unequal splits must sum to the total bill amount.")
            for participant, amount in custom_splits.items():
                if participant != bill.payer:
                    self.add_transaction(bill.payer, participant, amount)

        elif split_type == "By Percentage":
            if not custom_splits:
                raise ValueError("Custom splits required for 'percentage' mode.")
            total_percentage = sum(custom_splits.values())
            if abs(total_percentage - 100) > 0.01:
                raise ValueError("Percentages must sum to 100.")
            for participant, percentage in custom_splits.items():
                if participant != bill.payer:
                    self.add_transaction(bill.payer, participant, (bill.amount * percentage / 100))

        elif split_type == "By Shares":
            if not custom_splits:
                raise ValueError("Custom splits required for 'shares' mode.")
            total_shares = sum(custom_splits.values())
            for participant, shares in custom_splits.items():
                if participant != bill.payer:
                    share_amount = bill.amount * (shares / total_shares)
                    self.add_transaction(bill.payer, participant, share_amount)

        else:
            raise ValueError("Invalid split type. Use 'Equally', 'Custom', 'By Percentage', or 'By Shares'.")

        # Log the transaction
        self.transactions.append(transaction)

        # Update category totals
        if bill.category:
            self.category_totals[bill.category] += bill.amount



    def get_category_summary(self):
        """
        Generate a summary of expenses by category.
        Returns a dictionary of {category: total_amount}.
        """
        return dict(self.category_totals)

    def get_category_balances(self):
        """
        Generate balances for each category.
        Returns a dictionary of {category: {member: balance}}.
        """
        category_balances = defaultdict(lambda: defaultdict(float))
        for payer, payees in self.edges.items():
            for payee, amount in payees.items():
                for category, total in self.category_totals.items():
                    category_balances[category][payer] -= amount
                    category_balances[category][payee] += amount
        return category_balances
    
    def add_transaction(self, payer, payee, amount):
        """Add a transaction to the graph."""
        self.edges[payer][payee] += amount

    def get_transaction_history(self, filter_by=None):
        """
        Retrieve transaction history, optionally filtered by a key.
        filter_by: A dictionary specifying filters (e.g., {'category': 'Food'}).
        """
        if not filter_by:
            return self.transactions

        filtered_transactions = []
        for transaction in self.transactions:
            match = all(transaction.get(key) == value for key, value in filter_by.items())
            if match:
                filtered_transactions.append(transaction)
        return filtered_transactions
    
    def calculate_balances(self):
        """
        Calculate net balances for all members.
        Returns a dictionary of {member: net_balance}.
        """
        balance = defaultdict(float)
        for payer, payees in self.edges.items():
            for payee, amount in payees.items():
                balance[payer] -= amount
                balance[payee] += amount
        return dict(balance)

    def minimize_cash_flow(self):
        """
        Simplify the graph transactions to minimize cash flow.
        Returns a list of simplified transactions.
        """
        # Step 1: Calculate net balances
        balance = self.calculate_balances()
        net_balances = [(person, bal) for person, bal in balance.items() if bal != 0]

        def adjust_to_zero(net_balances, favor="creditor"):
            """
            Adjust balances to ensure total sums to zero.
            :param favor: 'creditor' (default) favors reducing creditor balances;
                        'debtor' favors increasing debtor balances.
            """
            total = sum(balance for _, balance in net_balances)
            if abs(total) > 0.01:  # If there is a rounding error
                if favor == "creditor":
                    # Adjust the largest positive balance
                    max_person, max_balance = max(net_balances, key=lambda x: x[1])
                    adjusted_balances = [
                        (person, balance if person != max_person else balance - total)
                        for person, balance in net_balances
                    ]
                elif favor == "debtor":
                    # Adjust the largest negative balance
                    min_person, min_balance = min(net_balances, key=lambda x: x[1])
                    adjusted_balances = [
                        (person, balance if person != min_person else balance - total)
                        for person, balance in net_balances
                    ]
                return adjusted_balances
            return net_balances

        # Step 2: Simplify using the algorithm
        def settle_debts(net_balances):
            if not net_balances:
                return []

            # Sort balances and find most positive and most negative
            net_balances = adjust_to_zero(net_balances)
            net_balances.sort(key=lambda x: x[1])
            min_person, min_amount = net_balances[0]  # Most negative
            max_person, max_amount = net_balances[-1]  # Most positive

            # Determine the settlement amount
            settle_amount = min(-min_amount, max_amount)

            # Log the transaction
            transaction = (min_person, max_person, settle_amount)

            # Update balances
            net_balances[0] = (min_person, min_amount + settle_amount)
            net_balances[-1] = (max_person, max_amount - settle_amount)

            # Remove zero balances
            net_balances = [entry for entry in net_balances if abs(entry[1]) > 0.01]

            # Recur with the updated balances
            return [transaction] + settle_debts(net_balances)

        return settle_debts(net_balances)
    
    def generate_networkx_graph(self):
        """
        Generate a NetworkX graph object from the current graph data.
        Returns:
            G (networkx.DiGraph): A directed graph representing the debts.
        """
        G = nx.DiGraph()
        for payer, payees in self.edges.items():
            for payee, amount in payees.items():
                G.add_edge(payer, payee, weight=amount)
        return G

    def visualize_graph(self):
        """
        Visualize the debt graph using Matplotlib and NetworkX.
        """
        G = self.generate_networkx_graph()

        # Set up layout and labels
        pos = nx.spring_layout(G)  # Layout algorithm
        edge_labels = nx.get_edge_attributes(G, 'weight')

        # Draw the graph
        nx.draw(G, pos, with_labels=True, node_color="lightblue", node_size=2000, font_size=10, font_weight="bold")
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

        # Show the plot
        plt.title("Debt Graph")
        plt.show()

if __name__ == "__main__":
    # Create a group
    group = Group(name="Trip to Paris")

    # Add members
    group.add_member("Alice", 'wweed')
    group.add_member("Bob")
    group.add_member("Charlie")

    # Add bills
    bill1 = Bill(payer="Alice", amount=300, participants=["Alice", "Bob", "Charlie"], category="Travel")
    group.add_bill(bill1, split_type="Equally")

    bill2 = Bill(payer="Bob", amount=150, participants=["Bob", "Charlie"], category="Food")
    group.add_bill(bill2, split_type="Equally")

    bill3 = Bill(payer="Bob", amount=450, participants=["Bob", "Charlie", "Alice"], category="Food")
    group.add_bill(bill3, split_type="Equally")

    # Example
    # amount_in_usd = convert_currency(100, "usd", "irtt")
    # print(f"Converted amount: {amount_in_usd:.2f}")


    # print(group.get_transaction_history())

    dick = group.graph.edges
    # print(dict(dick))

    mcf = group.graph.minimize_cash_flow()
    # print(mcf)

    # # Get summary
    # summary = group.get_summary()
    # print("Group Summary:")
    # print(summary)

    # # Remove a member
    # group.remove_member("Charlie")

    # # Get balances after removing Charlie
    # balances = group.get_balances()
    # print("\nBalances after removing Charlie:")
    # for member, balance in balances.items():
    #     print(f"{member}: {balance:.2f}")

    # # Delete the group
    # group.delete_group()