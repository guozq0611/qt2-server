-- 迁移脚本：为 future_info 表添加 currency 和 settle_type 字段
-- 适用于已有 future_info 表的环境（如从 quantlab/xquant 继承的库）
--
-- 用法:
--   mysql -h 127.0.0.1 -P 21707 -u root -p qt2 < schema/mysql/migrate_add_currency_settle_type.sql

ALTER TABLE future_info
  ADD COLUMN currency varchar(10) DEFAULT 'CNY' COMMENT '币种' AFTER product_id,
  ADD COLUMN settle_type varchar(10) DEFAULT 'PHYSICAL' COMMENT '交割方式: CASH=现金, PHYSICAL=实物' AFTER currency;

-- 回填已有数据的 settle_type（CFFEX=现金交割，其余=实物交割）
UPDATE future_info SET settle_type = 'CASH' WHERE exchange_id = 'CFFEX';
UPDATE future_info SET settle_type = 'PHYSICAL' WHERE exchange_id != 'CFFEX';
