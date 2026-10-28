"""Order data: schema/seed loading and the get_order tool.

Load the schema and seed with: uv run python -m supportpilot.orders
"""

from datetime import datetime
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel

from supportpilot import config

DB_DIR = config.REPO_ROOT / "backend" / "db"


class OrderItem(BaseModel):
    title: str
    author: str
    section: str
    is_signed: bool
    unit_price: Decimal
    discount: Decimal
    paid: Decimal


class Order(BaseModel):
    order_id: int
    status: str
    shipping_method: str
    shipping_cost: Decimal
    promotion: str | None
    created_at: datetime
    shipped_at: datetime | None
    delivered_at: datetime | None
    # Computed in SQL so the LLM never does date arithmetic.
    days_since_delivery: int | None
    # RETURN_WINDOW_DAYS - days_since_delivery, so the agent reads it instead of subtracting.
    # Negative: the window closed that many days ago.
    return_window_days_left: int | None
    items: list[OrderItem]


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        row_factory=dict_row,
    )


def get_order(order_id: int, customer_id: int) -> Order | None:
    """Return the order only if it belongs to customer_id.

    A missing order and another customer's order both return None, so callers can't tell them apart.
    """
    with connect() as conn:
        order = conn.execute(
            """
            SELECT id AS order_id, status, shipping_method, shipping_cost, promotion,
                   created_at, shipped_at, delivered_at,
                   (current_date - delivered_at::date) AS days_since_delivery
            FROM orders
            WHERE id = %s AND customer_id = %s
            """,
            (order_id, customer_id),
        ).fetchone()
        if order is None:
            return None

        items = conn.execute(
            """
            SELECT b.title, b.author, b.section, b.is_signed, oi.unit_price, oi.discount, oi.paid
            FROM order_items oi JOIN books b ON b.id = oi.book_id
            WHERE oi.order_id = %s
            ORDER BY b.title
            """,
            (order_id,),
        ).fetchall()

    days = order["days_since_delivery"]
    return Order(
        **order,
        return_window_days_left=None if days is None else config.RETURN_WINDOW_DAYS - days,
        items=[OrderItem(**item) for item in items],
    )


def get_latest_order(customer_id: int) -> Order | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM orders WHERE customer_id = %s ORDER BY created_at DESC LIMIT 1",
            (customer_id,),
        ).fetchone()
    return get_order(row["id"], customer_id) if row else None


def load_schema_and_seed() -> None:
    with connect() as conn:
        conn.execute((DB_DIR / "schema.sql").read_text())
        conn.execute((DB_DIR / "seed.sql").read_text())


if __name__ == "__main__":
    load_schema_and_seed()
    print("Loaded schema and seed data.")
