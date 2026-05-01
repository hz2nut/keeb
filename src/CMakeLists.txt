if(CONFIG_ZMK_DISPLAY)
  zephyr_library_sources(
    display/key_status.c
    display/status_screen.c
  )
  zephyr_library_include_directories(${CMAKE_CURRENT_SOURCE_DIR}/display)
endif()
