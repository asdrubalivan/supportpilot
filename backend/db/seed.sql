-- Dates are relative to now() so golden cases like "delivered 40 days ago" stay true over time.

INSERT INTO customers (id, name, email) VALUES
    (1, 'Ada Reader', 'ada@example.com'),        -- same emails as the Keycloak realm users
    (2, 'Basil Bookworm', 'basil@example.com');
-- Customers created on first login get ids after the seeded ones.
SELECT setval(pg_get_serial_sequence('customers', 'id'), 100);

INSERT INTO books (id, title, author, section, is_signed, price, stock) VALUES
    (1,  'Twenty Thousand Leagues Under the Seas', 'Jules Verne', 'adventure-sci-fi', false, 15.00, 12),
    (2,  'Around the World in Eighty Days', 'Jules Verne', 'adventure-sci-fi', false, 12.00, 8),
    (3,  'Pride and Prejudice', 'Jane Austen', 'classic-novels', false, 10.00, 20),
    (4,  'Moby Dick', 'Herman Melville', 'classic-novels', false, 14.00, 5),
    (5,  'Crime and Punishment', 'Fyodor Dostoevsky', 'classic-novels', false, 16.00, 7),
    (6,  'Meditations', 'Marcus Aurelius', 'philosophy', false, 9.00, 15),
    (7,  'How to Win Friends and Influence People', 'Dale Carnegie', 'self-help', false, 18.00, 10),
    (8,  'The Old Man and the Sea (signed)', 'Ernest Hemingway', 'classic-novels', true, 250.00, 1),
    (9,  'Don Quixote', 'Miguel de Cervantes', 'classic-novels', false, 20.00, 6),
    (10, 'The Time Machine', 'H. G. Wells', 'adventure-sci-fi', false, 11.00, 9);

INSERT INTO orders (id, customer_id, status, shipping_method, shipping_cost, promotion, created_at, shipped_at, delivered_at) VALUES
    -- Delivered 40 days ago: outside the 30-day return window.
    (1234, 1, 'delivered', 'standard', 4.99, 'jules-verne-discount', now() - interval '45 days', now() - interval '44 days', now() - interval '40 days'),
    -- Delivered 10 days ago, contains a signed copy (non-returnable) and a regular book.
    (1235, 1, 'delivered', 'express', 12.99, NULL, now() - interval '13 days', now() - interval '12 days', now() - interval '10 days'),
    -- 5-book order with "buy 5, get the cheapest free"; Meditations ($9) was free.
    (1236, 1, 'delivered', 'standard', 0.00, 'buy-5-get-the-cheapest-free', now() - interval '16 days', now() - interval '15 days', now() - interval '12 days'),
    -- In transit.
    (1237, 1, 'shipped', 'standard', 4.99, 'self-help-discount', now() - interval '3 days', now() - interval '2 days', NULL),
    -- Belongs to another customer: get_order for customer 1 must not reveal it.
    (1238, 2, 'delivered', 'standard', 4.99, NULL, now() - interval '9 days', now() - interval '8 days', now() - interval '5 days');

INSERT INTO order_items (order_id, book_id, unit_price, discount, paid) VALUES
    (1234, 1, 15.00, 3.00, 12.00),
    (1235, 8, 250.00, 0.00, 250.00),
    (1235, 3, 10.00, 0.00, 10.00),
    (1236, 3, 10.00, 0.00, 10.00),
    (1236, 4, 14.00, 0.00, 14.00),
    (1236, 5, 16.00, 0.00, 16.00),
    (1236, 6, 9.00, 9.00, 0.00),
    (1236, 9, 20.00, 0.00, 20.00),
    (1237, 7, 18.00, 9.00, 9.00),
    (1238, 10, 11.00, 0.00, 11.00);
