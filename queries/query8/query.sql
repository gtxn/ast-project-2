CREATE TABLE tbl_wqiwo (rcol_bjzii REAL, tcol_wskpp);
INSERT OR ABORT INTO tbl_wqiwo (tcol_wskpp) VALUES (11960.180152676927), (8446);
ALTER TABLE tbl_wqiwo ADD COLUMN icol_ovpnc INTEGER;
WITH with_vysww AS (SELECT * FROM tbl_wqiwo ORDER BY tbl_wqiwo.tcol_wskpp), with_kepqw AS (SELECT * FROM with_vysww GROUP BY with_vysww.icol_ovpnc ORDER BY with_vysww.rcol_bjzii) SELECT * FROM with_kepqw