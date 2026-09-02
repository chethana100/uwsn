# Install script for directory: /home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "debug")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-lr-wpan-debug.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-lr-wpan-debug.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-lr-wpan-debug.so"
         RPATH "/usr/local/lib:$ORIGIN/:$ORIGIN/../lib:/usr/local/lib64:$ORIGIN/:$ORIGIN/../lib64")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY FILES "/home/chethana/ns-allinone-3.41/ns-3.41/build/lib/libns3.41-lr-wpan-debug.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-lr-wpan-debug.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-lr-wpan-debug.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-lr-wpan-debug.so"
         OLD_RPATH "/home/chethana/ns-allinone-3.41/ns-3.41/build/lib::::::::::::::::::::::::::::::::"
         NEW_RPATH "/usr/local/lib:$ORIGIN/:$ORIGIN/../lib:/usr/local/lib64:$ORIGIN/:$ORIGIN/../lib64")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-lr-wpan-debug.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ns3" TYPE FILE FILES
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/helper/lr-wpan-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-constants.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-csmaca.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-error-model.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-fields.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-interference-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-lqi-tag.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-mac-header.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-mac-pl-headers.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-mac-trailer.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-mac-base.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-mac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-net-device.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-phy.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-spectrum-signal-parameters.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/lr-wpan/model/lr-wpan-spectrum-value-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/build/include/ns3/lr-wpan-module.h"
    )
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/home/chethana/ns-allinone-3.41/ns-3.41/cmake-cache/src/lr-wpan/examples/cmake_install.cmake")

endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/chethana/ns-allinone-3.41/ns-3.41/cmake-cache/src/lr-wpan/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
