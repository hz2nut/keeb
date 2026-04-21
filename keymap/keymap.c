#include QMK_KEYBOARD_H

enum my_layers {
	_HAZE,
	_QWERTY,
	_LOWER,
	_RAISE,
	_ADJUST,
};

enum my_keycodes {
	LANG1 = SAFE_RANGE,
	LANG2,
	L0CK,
};

#define LOWER LT(_LOWER, KC_SPC)
#define RAISE OSL(_RAISE)
#define DOTADJ LT(_ADJUST, KC_DOT)
#define TABADJ LT(_ADJUST, KC_TAB)
#define TMUX C(KC_B)

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
	[_HAZE] = LAYOUT(
			KC_K,    KC_C,    KC_G,    KC_M,    KC_J,                      KC_GRV,  KC_D,    KC_A,    KC_P,    KC_Y,
			KC_F,    KC_I,    KC_O,    KC_N,    KC_Q,                      KC_AT,   KC_R,    KC_E,    KC_T,    KC_S,
			KC_W,    KC_U,    KC_B,    KC_L,    KC_DLR,  _______, _______, KC_CIRC, KC_X,    KC_H,    KC_Z,    KC_V,
			OS_LGUI, OS_LCTL, OS_LALT, KC_BSPC, LOWER,   LANG1,   LANG2,   RAISE,   OS_RSFT, OS_RALT, OS_RCTL, OS_RGUI
			),

	[_QWERTY] = LAYOUT(
			KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,                      KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,
			KC_A,    KC_S,    KC_D,    KC_F,    KC_G,                      KC_H,    KC_J,    KC_K,    KC_L,    XXXXXXX,
			KC_Z,    KC_X,    KC_C,    KC_V,    _______, _______, _______, _______, KC_B,    KC_N,    KC_M,    XXXXXXX,
			_______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______
			),

	[_LOWER] = LAYOUT(
			KC_HOME, KC_PGDN, KC_PGUP, KC_END,  _______,                   KC_SLSH, KC_7,    KC_8,    KC_9,    KC_MINS,
			KC_LEFT, KC_DOWN, KC_UP,   KC_RGHT, _______,                   KC_ASTR, KC_4,    KC_5,    KC_6,    KC_PLUS,
			KC_DEL,  KC_INS,  TMUX,    KC_CAPS, _______, _______, _______, KC_EQL,  KC_1,    KC_2,    KC_3,    KC_0,
			_______, _______, _______, _______, _______, _______, _______, DOTADJ,  CW_TOGG, _______, _______, _______
			),

	[_RAISE] = LAYOUT(
			KC_LT,   KC_PLUS, KC_MINS, KC_GT,   KC_PERC,                   KC_HASH, KC_EQL,  KC_SLSH, KC_ASTR, KC_EXLM,
			KC_ESC,  KC_LPRN, KC_RPRN, KC_SCLN, KC_AMPR,                   KC_PIPE, KC_UNDS, KC_COMM, KC_DOT,  KC_ENT,
			KC_LCBR, KC_LBRC, KC_RBRC, KC_RCBR, KC_BSLS, _______, _______, KC_TILD, KC_COLN, KC_QUOT, KC_DQT,  KC_QUES,
			_______, _______, _______, KC_LEFT, TABADJ,  _______, _______, TMUX,    _______, _______, _______, _______
			),

	[_ADJUST] = LAYOUT(
			DM_REC2, DM_REC1, DM_PLY2, DM_PLY1, _______,                   KC_F15,  KC_F7,   KC_F8,   KC_F9,   KC_F12,
			KC_MRWD, KC_VOLD, KC_VOLU, KC_MFFD, _______,                   KC_F14,  KC_F4,   KC_F5,   KC_F6,   KC_F11,
			DM_RSTP, KC_BRID, KC_BRIU, KC_MPLY, _______, _______, _______, KC_F13,  KC_F1,   KC_F2,   KC_F3,   KC_F10,
			_______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______, _______
			),
};

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
	if(record->event.pressed) {
		switch(keycode) {
			case LANG1:
				tap_code16(C(KC_SPC));
			case LANG2:
				if (get_highest_layer(default_layer_state) == _HAZE)
					set_single_persistent_default_layer(_QWERTY);
				else
					set_single_persistent_default_layer(_HAZE);
				return false;
		}
	}
	return true;
}
