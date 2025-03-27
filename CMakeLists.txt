cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(Dosymetry)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/dosymetry")
set(EXTENSION_CATEGORY "Dosymetry")
set(EXTENSION_CONTRIBUTORS "Jakub Hulek (AGH University of Krakow)")
set(EXTENSION_DESCRIPTION "This extension was created for radiology experts to calibrate their equipement and plan treatment using raditation-sensitive stripes.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/dosymetry.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/dosymetry/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(film_calibration)
add_subdirectory(dosymetry)
add_subdirectory(gamma_analysis)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
