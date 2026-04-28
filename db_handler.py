from MARIADB_CREDS import DB_CONFIG
from mariadb import connect
from models.RentalHistory import RentalHistory
from models.Waitlist import Waitlist
from models.Item import Item
from models.Rental import Rental
from models.Customer import Customer
from datetime import date, timedelta


conn = connect(user=DB_CONFIG["username"], password=DB_CONFIG["password"], host=DB_CONFIG["host"],
               database=DB_CONFIG["database"], port=DB_CONFIG["port"])


cur = conn.cursor()


# * Completed
def add_item(new_item: Item = None):
    """
    new_item - An Item object containing a new item to be inserted into the DB in the item table.
        new_item and its attributes will never be None.
    """
    cur.execute("SELECT MAX(i_item_sk) FROM item")
    item_sk = (cur.fetchone()[0] or 0) + 1
    rec_start_date = f"{new_item.start_year}-01-01"

    cur.execute(
        """INSERT INTO item (i_item_sk, i_item_id, i_rec_start_date, i_product_name,
           i_brand, i_class, i_category, i_manufact, i_current_price, i_num_owned)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (item_sk, new_item.item_id, rec_start_date, new_item.product_name,
         new_item.brand, None, new_item.category, new_item.manufact,
         new_item.current_price, new_item.num_owned)
    )


def add_customer(new_customer: Customer = None):
    """
    new_customer - A Customer object containing a new customer to be inserted into the DB in the customer table.
        new_customer and its attributes will never be None.
    """
    street, city, state_and_zip = new_customer.address.split(", ")
    street_number, street_name = street.split(" ", 1)
    state, zip = state_and_zip.split(" ", 1)
    first_name, last_name = new_customer.name.split(" ", 1)

    cur.execute("SELECT MAX(ca_address_sk) FROM customer_address")
    addr_sk = (cur.fetchone()[0] or 0) + 1

    # BUG don't set the two cur next to each other
    cur.execute("SELECT MAX(c_customer_sk) FROM customer")
    customer_sk = (cur.fetchone()[0] or 0) + 1

    cur.execute(
        """INSERT INTO customer_address (ca_address_sk, ca_street_number, ca_street_name,
           ca_city, ca_state, ca_zip)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (addr_sk, street_number, street_name, city, state, zip)
    )

    cur.execute(
        """INSERT INTO customer (c_customer_sk, c_customer_id, c_first_name, c_last_name,
           c_email_address, c_current_addr_sk)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (customer_sk, new_customer.customer_id, first_name, last_name,
         new_customer.email, addr_sk)
    )


def edit_customer(original_customer_id: str = None, new_customer: Customer = None):
    """
    original_customer_id - A string containing the customer id for the customer to be edited.
    new_customer - A Customer object containing attributes to update. If an attribute is None, it should not be altered.
    """
    if new_customer.name is not None:
        first_name, last_name = new_customer.name.split(" ", 1)
        cur.execute("UPDATE customer SET c_first_name = ?, c_last_name = ? WHERE c_customer_id = ?",
                    (first_name, last_name, original_customer_id))

    if new_customer.email is not None:
        cur.execute("UPDATE customer SET c_email_address = ? WHERE c_customer_id = ?",
                    (new_customer.email, original_customer_id))

    if new_customer.address is not None:
        street, city, state_and_zip = new_customer.address.split(", ")
        street_number, street_name = street.split(" ", 1)
        state, zip_code = state_and_zip.split(" ", 1)

        cur.execute("SELECT c_current_addr_sk FROM customer WHERE c_customer_id = ?", (original_customer_id,))
        addr_sk = cur.fetchone()[0]

        cur.execute(
            """UPDATE customer_address
               SET ca_street_number = ?, ca_street_name = ?, ca_city = ?, ca_state = ?, ca_zip = ?
               WHERE ca_address_sk = ?""",
            (street_number, street_name, city, state, zip_code, addr_sk)
        )

    # To assume that original_cusotmer_id is set, that the default of None would not be a valid case
    # Thus this must be the last field to edit
    if new_customer.customer_id is not None:
        cur.execute("UPDATE customer SET c_customer_id = ? WHERE c_customer_id = ?",
                    (new_customer.customer_id, original_customer_id))


def rent_item(item_id: str = None, customer_id: str = None):
    """
    item_id - A string containing the Item ID for the item being rented.
    customer_id - A string containing the customer id of the customer renting the item.
    """
    rental_date = date.today()
    due_date = rental_date + timedelta(days=14)
    cur.execute(
        "INSERT INTO rental (item_id, customer_id, rental_date, due_date) VALUES (?, ?, ?, ?)",
        (item_id, customer_id, rental_date, due_date)
    )


def waitlist_customer(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's new place in line.
    """
    place_in_line = line_length(item_id) + 1
    cur.execute(
        "INSERT INTO waitlist (item_id, customer_id, place_in_line) VALUES (?, ?, ?)",
        (item_id, customer_id, place_in_line)
    )
    return place_in_line

def update_waitlist(item_id: str = None):
    """
    Removes person at position 1 and shifts everyone else down by 1.
    """
    raise NotImplementedError("you must implement this function")


def return_item(item_id: str = None, customer_id: str = None):
    """
    Moves a rental from rental to rental_history with return_date = today.
    """
    raise NotImplementedError("you must implement this function")


def grant_extension(item_id: str = None, customer_id: str = None):
    """
    Adds 14 days to the due_date.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    Returns a list of Item objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    Returns a list of Rental objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_rental_histories(filter_attributes: RentalHistory = None,
                                  min_rental_date: str = None,
                                  max_rental_date: str = None,
                                  min_due_date: str = None,
                                  max_due_date: str = None,
                                  min_return_date: str = None,
                                  max_return_date: str = None) -> list[RentalHistory]:
    """
    Returns a list of RentalHistory objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """
    raise NotImplementedError("you must implement this function")


def number_in_stock(item_id: str = None) -> int:
    """
    Returns num_owned - active rentals. Returns -1 if item doesn't exist.
    """
    raise NotImplementedError("you must implement this function")


def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's place_in_line, or -1 if not on waitlist.
    """
    cur.execute("SELECT place_in_line FROM waitlist WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id))
    row = cur.fetchone()
    return row[0] if row else -1


def line_length(item_id: str = None) -> int:
    """
    Returns how many people are on the waitlist for this item.
    """
    cur.execute("SELECT COUNT(*) FROM waitlist WHERE item_id = ?", (item_id,))
    return cur.fetchone()[0]


def save_changes():
    """
    Commits all changes made to the db.
    """
    raise NotImplementedError("you must implement this function")


def close_connection():
    """
    Closes the cursor and connection.
    """
    raise NotImplementedError("you must implement this function")
