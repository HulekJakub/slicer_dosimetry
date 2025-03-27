#-----------------------------------------------------------------------------
set(MODULE_NAME FilmCalibration)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  src/film_calibration_logic.py
  src/film_calibration_parameter_node.py
  src/film_calibration_widget.py
  src/imports.py
  src/marker_detection.py
  Testing/Python/example_test.py
)

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  # WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)
  slicer_add_python_unittest(SCRIPT Testing/Python/example_test.py)
  # Additional build-time testing
  add_subdirectory(Testing)
endif()
