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

# * Everything else
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
    cur.execute("DELETE FROM waitlist WHERE item_id = ? AND place_in_line = 1", (item_id,))
    cur.execute("UPDATE waitlist SET place_in_line = place_in_line - 1 WHERE item_id = ?", (item_id,))

def return_item(item_id: str = None, customer_id: str = None):
    """
    Moves a rental from rental to rental_history with return_date = today.
    """
    cur.execute("SELECT rental_date, due_date FROM rental WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id))
    rental_date, due_date = cur.fetchone()

    cur.execute(
        """INSERT INTO rental_history (item_id, customer_id, rental_date, due_date, return_date)
           VALUES (?, ?, ?, ?, ?)""",
        (item_id, customer_id, rental_date, due_date, date.today())
    )

    cur.execute("DELETE FROM rental WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id))

def grant_extension(item_id: str = None, customer_id: str = None):
    """
    Adds 14 days to the due_date.
    """
    cur.execute("SELECT due_date FROM rental WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id))

    due_date = cur.fetchone()[0] + timedelta(days=14)

    cur.execute("UPDATE rental SET due_date = ? WHERE item_id = ? AND customer_id = ?",
                (due_date, item_id, customer_id))

# * Filter items
def get_filtered_items(filter_attributes: Item = None,
                       use_patterns: bool = False,
                       min_price: float = -1,
                       max_price: float = -1,
                       min_start_year: int = -1,
                       max_start_year: int = -1) -> list[Item]:
    """
    Returns a list of Item objects matching the filters.
    """
    # CITE from stackoverflow for WHERE 1=1 for always true
    query = "SELECT i_item_id, i_product_name, i_brand, i_category, i_manufact, i_current_price, YEAR(i_rec_start_date), i_num_owned FROM item WHERE 1=1"
    params = []

    if use_patterns:
      operator = "LIKE"
    else:
      operator = "="

# ** Match filters
    if filter_attributes.item_id is not None:
       query += f" AND i_item_id {operator} ? "
       params.append(filter_attributes.item_id)
    if filter_attributes.product_name is not None:
       query += f" AND i_product_name {operator} ? "
       params.append(filter_attributes.product_name)
    if filter_attributes.brand is not None:
       query += f" AND i_brand {operator} ? "
       params.append(filter_attributes.brand)
    if filter_attributes.category is not None:
       query += f" AND i_category {operator} ? "
       params.append(filter_attributes.category)
    if filter_attributes.manufact is not None:
       query += f" AND i_manufact {operator} ? "
       params.append(filter_attributes.manufact)

# ** Integer filters
    if filter_attributes.current_price != -1:
        query += " AND i_current_price = ? "
        params.append(filter_attributes.current_price)
    if filter_attributes.start_year != -1:
        query += " AND YEAR(i_rec_start_date) = ? "
        params.append(filter_attributes.start_year)
    if filter_attributes.num_owned != -1:
        query += " AND i_num_owned = ? "
        params.append(filter_attributes.num_owned)

# ** Range filters
    if min_price != -1:
        query += " AND i_current_price >= ? "
        params.append(min_price)
    if max_price != -1:
        query += " AND i_current_price <= ? "
        params.append(max_price)
    if min_start_year != -1:
        query += " AND YEAR(i_rec_start_date) >= ? "
        params.append(min_start_year)
    if max_start_year != -1:
        query += " AND YEAR(i_rec_start_date) <= ? "
        params.append(max_start_year)

    cur.execute(query, tuple(params))

    results = []

    for _row in cur.fetchall():
        row = [col.strip() if isinstance(col, str) else col for col in _row]

        results.append(Item(
            item_id=row[0],
            product_name=row[1],
            brand=row[2],
            category=row[3],
            manufact=row[4],
            current_price=float(row[5]) if row[5] is not None else -1,
            start_year=row[6] if row[6] is not None else -1,
            num_owned=row[7] if row[7] is not None else -1
        ))

    return results

# * Filter customers
def get_filtered_customers(filter_attributes: Customer = None, use_patterns: bool = False) -> list[Customer]:
    """
    Returns a list of Customer objects matching the filters.
    """
    query = """SELECT c_customer_id, CONCAT(c_first_name, ' ', c_last_name),
               CONCAT(ca_street_number, ' ', ca_street_name, ', ', ca_city, ', ', ca_state, ' ', ca_zip),
               c_email_address
               FROM customer JOIN customer_address ON c_current_addr_sk = ca_address_sk
               WHERE 1=1"""
    params = []

    if use_patterns:
        operator = "LIKE"
    else:
        operator = "="

# ** Match filter
    if filter_attributes.customer_id is not None:
        query += f" AND c_customer_id {operator} ? "
        params.append(filter_attributes.customer_id)
    if filter_attributes.name is not None:
        query += f" AND CONCAT(c_first_name, ' ', c_last_name) {operator} ? "
        params.append(filter_attributes.name)
    if filter_attributes.email is not None:
        query += f" AND c_email_address {operator} ? "
        params.append(filter_attributes.email)
    if filter_attributes.address is not None:
        query += f" AND CONCAT(ca_street_number, ' ', ca_street_name, ', ', ca_city, ', ', ca_state, ' ', ca_zip) {operator} ? "
        params.append(filter_attributes.address)

    cur.execute(query, tuple(params))

    results = []
    for _row in cur.fetchall():
        row = [col.strip() if isinstance(col, str) else col for col in _row]

        results.append(Customer(
            customer_id=row[0],
            name=row[1],
            address=row[2],
            email=row[3]
        ))

    return results

# * Filter rentals
def get_filtered_rentals(filter_attributes: Rental = None,
                         min_rental_date: str = None,
                         max_rental_date: str = None,
                         min_due_date: str = None,
                         max_due_date: str = None) -> list[Rental]:
    """
    Returns a list of Rental objects matching the filters.
    """
    query = "SELECT item_id, customer_id, rental_date, due_date FROM rental WHERE 1=1"
    params = []

# ** Match filter
    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.rental_date is not None:
        query += " AND rental_date = ?"
        params.append(filter_attributes.rental_date)
    if filter_attributes.due_date is not None:
        query += " AND due_date = ?"
        params.append(filter_attributes.due_date)

# ** Range filter
    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)

    cur.execute(query, tuple(params))

    results = []
    for _row in cur.fetchall():
        row = [col.strip() if isinstance(col, str) else col for col in _row]

        results.append(Rental(
            item_id=row[0],
            customer_id=row[1],
            rental_date=str(row[2]),
            due_date=str(row[3])
        ))

    return results

# * Filter Rental History
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
    query = "SELECT item_id, customer_id, rental_date, due_date, return_date FROM rental_history WHERE 1=1"
    params = []

# ** Match Filters
    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.rental_date is not None:
        query += " AND rental_date = ?"
        params.append(filter_attributes.rental_date)
    if filter_attributes.due_date is not None:
        query += " AND due_date = ?"
        params.append(filter_attributes.due_date)
    if filter_attributes.return_date is not None:
        query += " AND return_date = ?"
        params.append(filter_attributes.return_date)

# ** Range Filters
    if min_rental_date is not None:
        query += " AND rental_date >= ?"
        params.append(min_rental_date)
    if max_rental_date is not None:
        query += " AND rental_date <= ?"
        params.append(max_rental_date)
    if min_due_date is not None:
        query += " AND due_date >= ?"
        params.append(min_due_date)
    if max_due_date is not None:
        query += " AND due_date <= ?"
        params.append(max_due_date)
    if min_return_date is not None:
        query += " AND return_date >= ?"
        params.append(min_return_date)
    if max_return_date is not None:
        query += " AND return_date <= ?"
        params.append(max_return_date)

    cur.execute(query, tuple(params))

    results = []
    for _row in cur.fetchall():
        row = [col.strip() if isinstance(col, str) else col for col in _row]

        results.append(RentalHistory(
            item_id=row[0],
            customer_id=row[1],
            rental_date=str(row[2]),
            due_date=str(row[3]),
            return_date=str(row[4])
        ))

    return results

# * Filter waitlist
def get_filtered_waitlist(filter_attributes: Waitlist = None,
                          min_place_in_line: int = -1,
                          max_place_in_line: int = -1) -> list[Waitlist]:
    """
    Returns a list of Waitlist objects matching the filters.
    """
    query = "SELECT item_id, customer_id, place_in_line FROM waitlist WHERE 1=1"
    params = []

# ** Match filter
    if filter_attributes.item_id is not None:
        query += " AND item_id = ?"
        params.append(filter_attributes.item_id)
    if filter_attributes.customer_id is not None:
        query += " AND customer_id = ?"
        params.append(filter_attributes.customer_id)
    if filter_attributes.place_in_line != -1:
        query += " AND place_in_line = ?"
        params.append(filter_attributes.place_in_line)

# ** Range filter
    if min_place_in_line != -1:
        query += " AND place_in_line >= ?"
        params.append(min_place_in_line)
    if max_place_in_line != -1:
        query += " AND place_in_line <= ?"
        params.append(max_place_in_line)

    cur.execute(query, tuple(params))

    results = []
    for _row in cur.fetchall():
        row = [col.strip() if isinstance(col, str) else col for col in _row]

        results.append(Waitlist(
            item_id=row[0],
            customer_id=row[1],
            place_in_line=row[2]
        ))

    return results

# * Everything else
def number_in_stock(item_id: str = None) -> int:
    """
    Returns num_owned - active rentals. Returns -1 if item doesn't exist.
    """
    cur.execute("SELECT i_num_owned FROM item WHERE i_item_id = ?", (item_id,))
    item = cur.fetchone()

    if item is None:
        return -1

    cur.execute("SELECT COUNT(*) FROM rental WHERE item_id = ?", (item_id,))
    rental = cur.fetchone()[0]

    return item[0] - rental

def place_in_line(item_id: str = None, customer_id: str = None) -> int:
    """
    Returns the customer's place_in_line, or -1 if not on waitlist.
    """
    cur.execute("SELECT place_in_line FROM waitlist WHERE item_id = ? AND customer_id = ?",
                (item_id, customer_id))
    row = cur.fetchone()

    if row is None:
        return -1

    return row[0]

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
    conn.commit()

def close_connection():
    """
    Closes the cursor and connection.
    """
    cur.close()
    conn.close()
