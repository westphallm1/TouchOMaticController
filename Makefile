touch_o_matic.py: touch-o-matic-tabbed.ui
	pyuic5 touch-o-matic-tabbed.ui > touch_o_matic.py
test: touch_o_matic.py
	python gui.py 
	
