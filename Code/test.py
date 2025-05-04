from ABB_control import set_pause_printing, set_piece_choice, fetch_layer


set_piece_choice(2)
set_pause_printing(False)
while True:
    layer = fetch_layer()
    if layer:
        set_pause_printing(True)
        break

set_piece_choice(3)
set_pause_printing(False)



