/*
 * Copyright (c) 2025 The ZMK Contributors
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zmk/display.h>
#include "key_status.h"

static struct zmk_widget_key_status key_widget;

lv_obj_t *zmk_display_status_screen(void) {
	lv_obj_t *screen = lv_obj_create(NULL);

	zmk_widget_key_status_init(&key_widget, screen);

	return screen;
}
