default:
	pyuic5 touch-o-matic.ui > touch_o_matic.py
test: default 
	python gui.py 
	
