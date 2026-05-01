/*
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 */

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

/* ------------------------------------------------------------------ */
/*  Keycode → display string                                           */
/* ------------------------------------------------------------------ */

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
/*  Key press listener                                                 */
/* ------------------------------------------------------------------ */

struct key_state { char key_str[8]; };

static void key_update_cb(struct key_state state) {
    struct zmk_widget_key_status *w;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) {
        const lv_font_t *font = (strlen(state.key_str) == 1)
            ? &lv_font_montserrat_26 : &lv_font_montserrat_16;
        lv_obj_set_style_text_font(w->key_label, font, 0);
        lv_label_set_text(w->key_label, state.key_str);
        lv_obj_align(w->key_label, LV_ALIGN_CENTER, 0, 0);
    }
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

/* ------------------------------------------------------------------ */
/*  Layer listener                                                     */
/* ------------------------------------------------------------------ */

struct layer_state { uint8_t index; const char *label; };

static void layer_update_cb(struct layer_state state) {
    char text[16];
    if (state.label != NULL && state.label[0] != '\0') {
        strncpy(text, state.label, sizeof(text) - 1);
        text[sizeof(text) - 1] = '\0';
    } else {
        snprintf(text, sizeof(text), "LYR %d", state.index);
    }
    struct zmk_widget_key_status *w;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) {
        lv_label_set_text(w->layer_label, text);
    }
}

static struct layer_state layer_get_state(const zmk_event_t *eh) {
    zmk_keymap_layer_index_t idx = zmk_keymap_highest_layer_active();
    return (struct layer_state){
        .index = idx,
        .label = zmk_keymap_layer_name(zmk_keymap_layer_index_to_id(idx)),
    };
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_layer, struct layer_state, layer_update_cb, layer_get_state)
ZMK_SUBSCRIPTION(widget_layer, zmk_layer_state_changed);

/* ------------------------------------------------------------------ */
/*  Battery listener                                                   */
/* ------------------------------------------------------------------ */

struct battery_state { uint8_t level; };

static void battery_update_cb(struct battery_state state) {
    char text[8];
    snprintf(text, sizeof(text), "%d%%", state.level);
    struct zmk_widget_key_status *w;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) {
        lv_label_set_text(w->battery_label, text);
    }
}

static struct battery_state battery_get_state(const zmk_event_t *eh) {
    return (struct battery_state){
        .level = zmk_battery_state_of_charge(),
    };
}

ZMK_DISPLAY_WIDGET_LISTENER(widget_battery, struct battery_state, battery_update_cb, battery_get_state)
ZMK_SUBSCRIPTION(widget_battery, zmk_battery_state_changed);

/* ------------------------------------------------------------------ */
/*  Connection/endpoint listener                                       */
/* ------------------------------------------------------------------ */

struct conn_state {
    enum zmk_transport transport;
    uint8_t ble_profile;
    bool ble_connected;
};

static void conn_update_cb(struct conn_state state) {
    char text[8];
    if (state.transport == ZMK_TRANSPORT_USB) {
        snprintf(text, sizeof(text), "USB");
    } else if (state.ble_connected) {
        snprintf(text, sizeof(text), "BT:%d", state.ble_profile + 1);
    } else {
        snprintf(text, sizeof(text), "X");
    }
    struct zmk_widget_key_status *w;
    SYS_SLIST_FOR_EACH_CONTAINER(&widgets, w, node) {
        lv_label_set_text(w->conn_label, text);
        lv_obj_align(w->conn_label, LV_ALIGN_TOP_RIGHT, -2, 2);
    }
}

static struct conn_state conn_get_state(const zmk_event_t *eh) {
    struct zmk_endpoint_instance ep = zmk_endpoints_selected();
    struct conn_state s = {
        .transport = ep.transport,
        .ble_profile = 0,
        .ble_connected = false,
    };
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
/*  Widget init                                                        */
/* ------------------------------------------------------------------ */

int zmk_widget_key_status_init(struct zmk_widget_key_status *widget, lv_obj_t *parent) {
    widget->battery_label = lv_label_create(parent);
    lv_obj_set_style_text_font(widget->battery_label, &lv_font_montserrat_14, LV_PART_MAIN);
    lv_obj_set_style_text_color(widget->battery_label, lv_color_black(), LV_PART_MAIN);
    lv_label_set_text(widget->battery_label, "---");
    lv_obj_align(widget->battery_label, LV_ALIGN_TOP_LEFT, 2, 2);

    widget->conn_label = lv_label_create(parent);
    lv_obj_set_style_text_font(widget->conn_label, &lv_font_montserrat_14, LV_PART_MAIN);
    lv_obj_set_style_text_color(widget->conn_label, lv_color_black(), LV_PART_MAIN);
    lv_label_set_text(widget->conn_label, "---");
    lv_obj_align(widget->conn_label, LV_ALIGN_TOP_RIGHT, -2, 2);

    widget->key_label = lv_label_create(parent);
    lv_obj_set_style_text_font(widget->key_label, &lv_font_montserrat_26, LV_PART_MAIN);
    lv_obj_set_style_text_color(widget->key_label, lv_color_black(), LV_PART_MAIN);
    lv_label_set_text(widget->key_label, "---");
    lv_obj_align(widget->key_label, LV_ALIGN_CENTER, 0, 0);

    widget->layer_label = lv_label_create(parent);
    lv_obj_set_style_text_font(widget->layer_label, &lv_font_montserrat_14, LV_PART_MAIN);
    lv_obj_set_style_text_color(widget->layer_label, lv_color_black(), LV_PART_MAIN);
    lv_label_set_text(widget->layer_label, "---");
    lv_obj_align(widget->layer_label, LV_ALIGN_BOTTOM_MID, 0, -2);

    sys_slist_append(&widgets, &widget->node);
    widget_key_init();
    widget_layer_init();
    widget_battery_init();
    widget_conn_init();

    return 0;
}
