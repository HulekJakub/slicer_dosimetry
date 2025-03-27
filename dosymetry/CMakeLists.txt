#-----------------------------------------------------------------------------
set(MODULE_NAME dosymetry)


#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME_FILE}.py
  src/dosymetry_logic.py
  src/dosymetry_parameter_node.py
  src/dosymetry_widget.py
  src/utils.py
  src/optimize.py
  src/logic_subprocess.py
  src/detect_dosymetry_stripes.py
  src/dosymetry_settings_widget.py
  Testing/Python/example_test.py
)

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME_FILE}.png
  Resources/UI/${MODULE_NAME_FILE}.ui
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
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME_FILE}.py)
  slicer_add_python_unittest(SCRIPT Testing/Python/example_test.py)
  # Additional build-time testing
  add_subdirectory(Testing)
endif()
