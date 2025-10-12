find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_COSPAS gnuradio-cospas)

FIND_PATH(
    GR_COSPAS_INCLUDE_DIRS
    NAMES gnuradio/cospas/api.h
    HINTS $ENV{COSPAS_DIR}/include
        ${PC_COSPAS_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_COSPAS_LIBRARIES
    NAMES gnuradio-cospas
    HINTS $ENV{COSPAS_DIR}/lib
        ${PC_COSPAS_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-cospasTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_COSPAS DEFAULT_MSG GR_COSPAS_LIBRARIES GR_COSPAS_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_COSPAS_LIBRARIES GR_COSPAS_INCLUDE_DIRS)
