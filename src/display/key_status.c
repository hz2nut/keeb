/*
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 */

#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zmk/display.h>
#include <zmk/event_manager.h>
#include <zmk/events/keycode_state_changed.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/battery_state_changed.h>
#include <zmk/events/endpoint_changed.h>
#include <zmk/hid.h>
#include <zmk/keymap.h>
#include <zmk/battery.h>
#include <zmk/endpoints.h>
#if IS_ENABLED(CONFIG_ZMK_BLE)
#include <zmk/ble.h>
#endif
#include "key_status.h"

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

static sys_slist_t widgets = SYS_SLIST_STATIC_INIT(&widgets);

#define KB_PAGE   0x07
#define MOD_SHIFT 0x22  /* LSHIFT(0x02) | RSHIFT(0x20) */

static struct {
	uint8_t battery;
	char conn[8];
	char key[8];
	char layer[16];
} active_state = {
	.battery = 0,
	.conn = "---",
	.key = "---",
	.layer = "LYR"
};

static char last_key[8] = "";

static void keycode_to_str(uint16_t page, uint32_t kc, uint8_t mods, char *buf, size_t len) {
	if (page != KB_PAGE) { buf[0] = '\0'; return; }
	bool sh = (mods & MOD_SHIFT) != 0;

	if (kc >= 0x04 && kc <= 0x1D) {
		snprintf(buf, len, "%c", 'A' + (kc - 0x04));
		return;
	}

	static const char base[] = "1234567890";
	static const char shft[] = "!@#$%^&*()";
	if (kc >= 0x1E && kc <= 0x27) {
		snprintf(buf, len, "%c", sh ? shft[kc - 0x1E] : base[kc - 0x1E]);
		return;
	}

	switch (kc) {
		case 0x28: snprintf(buf, len, "ENT"); return;
		case 0x29: snprintf(buf, len, "ESC"); return;
		case 0x2A: snprintf(buf, len, "BSP"); return;
		case 0x2B: snprintf(buf, len, "TAB"); return;
		case 0x2C: snprintf(buf, len, "SPC"); return;
		case 0x4F: snprintf(buf, len, "→");   return;
		case 0x50: snprintf(buf, len, "←");   return;
		case 0x51: snprintf(buf, len, "↓");   return;
		case 0x52: snprintf(buf, len, "↑");   return;
		case 0x4A: snprintf(buf, len, "HOM"); return;
		case 0x4D: snprintf(buf, len, "END"); return;
		case 0x4B: snprintf(buf, len, "PGU"); return;
		case 0x4E: snprintf(buf, len, "PGD"); return;
		case 0x4C: snprintf(buf, len, "DEL"); return;
		case 0x39: snprintf(buf, len, "CAP"); return;
		case 0x2D: snprintf(buf, len, sh ? "_" : "-"); return;
		case 0x2E: snprintf(buf, len, sh ? "+" : "="); return;
		case 0x2F: snprintf(buf, len, sh ? "{" : "["); return;
		case 0x30: snprintf(buf, len, sh ? "}" : "]"); return;
		case 0x31: snprintf(buf, len, sh ? "|" : "\\"); return;
		case 0x33: snprintf(buf, len, sh ? ":" : ";"); return;
		case 0x34: snprintf(buf, len, sh ? "\"" : "'"); return;
		case 0x35: snprintf(buf, len, sh ? "~" : "`"); return;
		case 0x36: snprintf(buf, len, sh ? "<" : ","); return;
		case 0x37: snprintf(buf, len, sh ? ">" : "."); return;
		case 0x38: snprintf(buf, len, sh ? "?" : "/"); return;
		default:   buf[0] = '\0'; return;
	}
}

/* ------------------------------------------------------------------ */
/*  Drawing helpers                                                     */
/* ------------------------------------------------------------------ */

static void canvas_draw_str(lv_obj_t *canvas, lv_coord_t x, lv_coord_t y, lv_coord_t max_w,
                             lv_color_t color, const lv_font_t *font, lv_text_align_t align,
                             const char *txt) {
	lv_draw_label_dsc_t dsc;
	lv_draw_label_dsc_init(&dsc);
	dsc.color = color;
	dsc.font = font;
	dsc.align = align;
	lv_canvas_draw_text(canvas, x, y, max_w, &dsc, txt);
}

static void rotate_canvas(lv_obj_t *canvas, lv_color_t cbuf[]) {
	static lv_color_t cbuf_tmp[CANVAS_SIZE * CANVAS_SIZE];
	memcpy(cbuf_tmp, cbuf, sizeof(cbuf_tmp));
	lv_img_dsc_t img;
	img.data = (void *)cbuf_tmp;
	img.header.cf = LV_IMG_CF_TRUE_COLOR;
	img.header.w = CANVAS_SIZE;
	img.header.h = CANVAS_SIZE;
	lv_canvas_fill_bg(canvas, lv_color_black(), LV_OPA_COVER);
	lv_canvas_transform(canvas, &img, 900, LV_IMG_ZOOM_NONE, -1, 0,
	                    CANVAS_SIZE / 2, CANVAS_SIZE / 2, true);
}

/* ------------------------------------------------------------------ */
/*  Widget draw functions                                               */
/* ------------------------------------------------------------------ */

static void draw_top(struct zmk_widget_key_status *w) {
	lv_obj_t *canvas = lv_obj_get_child(w->obj, 0);
	lv_canvas_fill_bg(canvas, lv_color_black(), LV_OPA_COVER);

	char bat_str[8];
	snprintf(bat_str, sizeof(bat_str), "%d%%", active_state.battery);

	canvas_draw_str(canvas, 0, 2, 34, lv_color_white(),
	                &lv_font_montserrat_14, LV_TEXT_ALIGN_LEFT, active_state.conn);
	canvas_draw_str(canvas, 34, 2, 34, lv_color_white(),
	                &lv_font_montserrat_14, LV_TEXT_ALIGN_RIGHT, bat_str);
	rotate_canvas(canvas, w->cbuf_top);
}

static void draw_mid(struct zmk_widget_key_status *w) {
	lv_obj_t *canvas = lv_obj_get_child(w->obj, 1);
	lv_canvas_fill_bg(canvas, lv_color_black(), LV_OPA_COVER);

	bool single = (strlen(active_state.key) == 1);
	const lv_font_t *font = single ? &lv_font_montserrat_26 : &lv_font_montserrat_16;
	lv_coord_t y_off = single ? 21 : 26;

	canvas_draw_str(canvas, 0, y_off, CANVAS_SIZE, lv_color_white(),
	                font, LV_TEXT_ALIGN_CENTER, active_state.key);
	rotate_canvas(canvas, w->cbuf_mid);
}

static void draw_btm(struct zmk_widget_key_status *w) {
	lv_obj_t *canvas = lv_obj_get_child(w->obj, 2);
	lv_canvas_fill_bg(canvas, lv_color_black(), LV_OPA_COVER);

	canvas_draw_str(canvas, 0, 5, CANVAS_SIZE, lv_color_white(),
	                &lv_font_montserrat_14, LV_TEXT_ALIGN_CENTER, active_state.layer);
	rotate_canvas(canvas, w->cbuf_btm);
}

/* ------------------------------------------------------------------ */
/*  Event listeners                                                     */
/* ------------------------------------------------------------------ */

struct key_state { char key_str[8]; };
static void key_update_cb(struct key_state state) {
	strncpy(active_state.key, state.key_str, sizeof(active_state.key));
	struct zmk_widget_key_status *w;
	SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) { draw_mid(w); }
}
static struct key_state key_get_state(const zmk_event_t *eh) {
	const struct zmk_keycode_state_changed *ev = as_zmk_keycode_state_changed(eh);
	if (ev != NULL && ev->state && !is_mod(ev->usage_page, ev->keycode)) {
		keycode_to_str(ev->usage_page, ev->keycode,
		               ev->implicit_modifiers | ev->explicit_modifiers,
		               last_key, sizeof(last_key));
	}
	struct key_state s;
	strncpy(s.key_str, last_key, sizeof(s.key_str));
	return s;
}
ZMK_DISPLAY_WIDGET_LISTENER(widget_key, struct key_state, key_update_cb, key_get_state)
ZMK_SUBSCRIPTION(widget_key, zmk_keycode_state_changed);

struct layer_state { uint8_t index; const char *label; };
static void layer_update_cb(struct layer_state state) {
	if (state.label != NULL && state.label[0] != '\0') {
		strncpy(active_state.layer, state.label, sizeof(active_state.layer) - 1);
	} else {
		snprintf(active_state.layer, sizeof(active_state.layer), "LYR %d", state.index);
	}
	struct zmk_widget_key_status *w;
	SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) { draw_btm(w); }
}
static struct layer_state layer_get_state(const zmk_event_t *eh) {
	zmk_keymap_layer_index_t idx = zmk_keymap_highest_layer_active();
	return (struct layer_state){
		.index = idx,
		.label = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(idx))
	};
}
ZMK_DISPLAY_WIDGET_LISTENER(widget_layer, struct layer_state, layer_update_cb, layer_get_state)
ZMK_SUBSCRIPTION(widget_layer, zmk_layer_state_changed);

struct battery_state { uint8_t level; };
static void battery_update_cb(struct battery_state state) {
	active_state.battery = state.level;
	struct zmk_widget_key_status *w;
	SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) { draw_top(w); }
}
static struct battery_state battery_get_state(const zmk_event_t *eh) {
	return (struct battery_state){ .level = zmk_battery_state_of_charge() };
}
ZMK_DISPLAY_WIDGET_LISTENER(widget_battery, struct battery_state, battery_update_cb, battery_get_state)
ZMK_SUBSCRIPTION(widget_battery, zmk_battery_state_changed);

struct conn_state { enum zmk_transport transport; uint8_t ble_profile; bool ble_connected; };
static void conn_update_cb(struct conn_state state) {
	if (state.transport == ZMK_TRANSPORT_USB) {
		snprintf(active_state.conn, sizeof(active_state.conn), "U");
	} else if (state.ble_connected) {
		snprintf(active_state.conn, sizeof(active_state.conn), "%d", state.ble_profile + 1);
	} else {
		snprintf(active_state.conn, sizeof(active_state.conn), "X");
	}
	struct zmk_widget_key_status *w;
	SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) { draw_top(w); }
}
static struct conn_state conn_get_state(const zmk_event_t *eh) {
	struct zmk_endpoint_instance ep = zmk_endpoints_selected();
	struct conn_state s = { .transport = ep.transport, .ble_profile = 0, .ble_connected = false };
#if IS_ENABLED(CONFIG_ZMK_BLE)
	if (ep.transport == ZMK_TRANSPORT_BLE) {
		s.ble_profile = zmk_ble_active_profile_index();
		s.ble_connected = zmk_ble_active_profile_is_connected();
	}
#endif
	return s;
}
ZMK_DISPLAY_WIDGET_LISTENER(widget_conn, struct conn_state, conn_update_cb, conn_get_state)
ZMK_SUBSCRIPTION(widget_conn, zmk_endpoint_changed);

/* ------------------------------------------------------------------ */
/*  Widget init                                                         */
/* ------------------------------------------------------------------ */

int zmk_widget_key_status_init(struct zmk_widget_key_status *widget, lv_obj_t *parent) {
	widget->obj = lv_obj_create(parent);
	lv_obj_set_size(widget->obj, 160, 68);

	lv_obj_t *canvas_top = lv_canvas_create(widget->obj);
	lv_obj_align(canvas_top, LV_ALIGN_TOP_RIGHT, 0, 0);
	lv_canvas_set_buffer(canvas_top, widget->cbuf_top, CANVAS_SIZE, CANVAS_SIZE,
	                     LV_IMG_CF_TRUE_COLOR);

	lv_obj_t *canvas_mid = lv_canvas_create(widget->obj);
	lv_obj_align(canvas_mid, LV_ALIGN_TOP_LEFT, 24, 0);
	lv_canvas_set_buffer(canvas_mid, widget->cbuf_mid, CANVAS_SIZE, CANVAS_SIZE,
	                     LV_IMG_CF_TRUE_COLOR);

	lv_obj_t *canvas_btm = lv_canvas_create(widget->obj);
	lv_obj_align(canvas_btm, LV_ALIGN_TOP_LEFT, -44, 0);
	lv_canvas_set_buffer(canvas_btm, widget->cbuf_btm, CANVAS_SIZE, CANVAS_SIZE,
	                     LV_IMG_CF_TRUE_COLOR);

	sys_slist_append(&widgets, &widget->node);
	widget_key_init();
	widget_layer_init();
	widget_battery_init();
	widget_conn_init();

	return 0;
}

lv_obj_t *zmk_widget_key_status_obj(struct zmk_widget_key_status *widget) {
	return widget->obj;
}
