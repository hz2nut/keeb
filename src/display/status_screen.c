/*
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 */

#include <zmk/display.h>
#include "key_status.h"

static struct zmk_widget_key_status key_widget;

lv_obj_t *zmk_display_status_screen(void) {
    /* Rotate virtual coordinate space to match physical portrait mounting.
     * Driver gives 160×68 landscape; after 270° rotation LVGL sees 68×160. */
    lv_display_set_rotation(lv_display_get_default(), LV_DISPLAY_ROTATION_270);

    lv_obj_t *screen = lv_obj_create(NULL);
    lv_obj_set_style_bg_color(screen, lv_color_white(), 0);
    lv_obj_set_style_pad_all(screen, 0, 0);
    lv_obj_set_style_border_width(screen, 0, 0);

    zmk_widget_key_status_init(&key_widget, screen);

    return screen;
}
