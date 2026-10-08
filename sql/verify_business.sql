-- Read-only business verification. Only connect to 127.0.0.1:13306 / litemall_qa.
-- Set these from evidence/http.jsonl (IDs vary on each real run).
SET @order_id = 0;
SET @product_id = 1;
SET @cart_id = 0;
SET @test_user_id = 0;

SELECT DATABASE() AS current_database, @@port AS mysql_port;
SELECT id,user_id,order_sn,order_status,goods_price,freight_price,coupon_price,actual_price,deleted
FROM litemall_order WHERE id=@order_id;
SELECT order_id,product_id,goods_id,number,price,price*number AS line_total
FROM litemall_order_goods WHERE order_id=@order_id;
SELECT o.id,o.goods_price,SUM(og.price*og.number) AS expected_goods_price,
       o.goods_price=SUM(og.price*og.number) AS amount_matches
FROM litemall_order o JOIN litemall_order_goods og ON og.order_id=o.id
WHERE o.id=@order_id GROUP BY o.id,o.goods_price;
SELECT id,goods_id,number,price FROM litemall_goods_product WHERE id=@product_id;
SELECT id,user_id,goods_id,product_id,number,deleted FROM litemall_cart WHERE id=@cart_id;
-- Goods/product consistency evidence (BUG-003).
SELECT c.id,c.goods_id,c.product_id,p.goods_id AS actual_product_goods_id,
       c.goods_id=p.goods_id AS relationship_valid
FROM litemall_cart c JOIN litemall_goods_product p ON p.id=c.product_id
WHERE c.user_id=@test_user_id AND c.deleted=0;
-- Evidence retains snapshots because fixture cleanup removes only its own test records.
SELECT COUNT(*) AS remaining_fixture_users FROM litemall_user WHERE LEFT(username,7)='qa_run_';
