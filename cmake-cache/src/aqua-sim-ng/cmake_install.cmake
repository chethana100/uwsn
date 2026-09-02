# Install script for directory: /home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng

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
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-aqua-sim-ng-debug.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-aqua-sim-ng-debug.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-aqua-sim-ng-debug.so"
         RPATH "/usr/local/lib:$ORIGIN/:$ORIGIN/../lib:/usr/local/lib64:$ORIGIN/:$ORIGIN/../lib64")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY FILES "/home/chethana/ns-allinone-3.41/ns-3.41/build/lib/libns3.41-aqua-sim-ng-debug.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-aqua-sim-ng-debug.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-aqua-sim-ng-debug.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-aqua-sim-ng-debug.so"
         OLD_RPATH "/home/chethana/ns-allinone-3.41/ns-3.41/build/lib::::::::::::::::::::::::::::::::"
         NEW_RPATH "/usr/local/lib:$ORIGIN/:$ORIGIN/../lib:/usr/local/lib64:$ORIGIN/:$ORIGIN/../lib64")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libns3.41-aqua-sim-ng-debug.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ns3" TYPE FILE FILES
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-application.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-address.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-pt-tag.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-channel.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-energy-model.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-hash-table.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-header.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-header-goal.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-header-mac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mobility-pattern.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-modulation.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-net-device.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-node.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-noise-generator.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-phy.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-phy-cmn.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-propagation.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-range-propagation.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-simple-propagation.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-signal-cache.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-sinr-checker.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/helper/aqua-sim-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-broadcast.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-fama.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-aloha.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-copemac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-goal.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-sfama.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-libra.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-trumac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-jmac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-tdma.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mac-uwan.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-rmac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-rmac-buffer.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-tmac.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-static.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-header-routing.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-dynamic.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-flooding.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-datastructure.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-buffer.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-vbf.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-trustq-vbf.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-dbr.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-vbva.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mobility-kinematic.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-mobility-rwp.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-synchronization.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-localization.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-ddos.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-attack-model.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-trace-reader.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-time-tag.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/named-data.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/named-data-header.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/name-discovery.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/pit.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/fib.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/content-storage.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/cs-fifo.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/cs-lru.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/cs-random.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/ndn/onoff-nd-application.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/helper/named-data-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/helper/on-off-nd-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/helper/aqua-sim-application-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/helper/aqua-sim-traffic-gen-helper.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-traffic-gen.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-dummy.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/aqua-sim-routing-ddbr.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/src/aqua-sim-ng/model/lib/svm.h"
    "/home/chethana/ns-allinone-3.41/ns-3.41/build/include/ns3/aqua-sim-ng-module.h"
    )
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/chethana/ns-allinone-3.41/ns-3.41/cmake-cache/src/aqua-sim-ng/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
