# Copyright (C) 2017-2018  Andrew Gunnerson <andrewgunnerson@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

FROM registry.fedoraproject.org/fedora:28

# Install gosu
ENV GOSU_VERSION 1.10
RUN dnf -y install gnupg \
    && curl -Lo /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-amd64" \
    && curl -Lo /tmp/gosu.asc "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-amd64.asc" \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg --keyserver keyserver.ubuntu.com \
        --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
    && gpg --batch --verify /tmp/gosu.asc /usr/local/bin/gosu \
    && rm -r "${GNUPGHOME}" /tmp/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && gosu nobody true \
    && dnf -y remove gnupg \
    && dnf clean all

# Install tini
ENV TINI_VERSION v0.16.1
RUN dnf -y install gnupg \
    && curl -Lo /usr/local/bin/tini "https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini" \
    && curl -Lo /tmp/tini.asc "https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini.asc" \
    && export GNUPGHOME="$(mktemp -d)" \
    && gpg --keyserver keyserver.ubuntu.com \
        --recv-keys 595E85A6B1B4779EA4DAAEC70B588DFF0527A9B7 \
    && gpg --batch --verify /tmp/tini.asc /usr/local/bin/tini \
    && rm -r "${GNUPGHOME}" /tmp/tini.asc \
    && chmod +x /usr/local/bin/tini \
    && dnf -y remove gnupg \
    && dnf clean all

# Install zipalign
ARG ANDROID_SDK_VERSION=3859397
ARG ANDROID_SDK_CHECKSUM=444e22ce8ca0f67353bda4b85175ed3731cae3ffa695ca18119cbacef1c1bea0
ARG ANDROID_HOME=/opt/android-sdk
ARG ANDROID_BUILD_TOOLS_VERSION=27.0.3

# Change to "sdkmanager --licenses" once it's available in a stable release
# Chromium's Android tools repo usually has the checksum for the latest license:
# https://chromium.googlesource.com/android_tools/+/refs/heads/master/sdk/licenses/android-sdk-license
RUN mkdir ${ANDROID_HOME} \
    && cd ${ANDROID_HOME} \
    && dnf install -y aria2 java-1.8.0-openjdk unzip \
    && aria2c -x4 https://dl.google.com/android/repository/sdk-tools-linux-${ANDROID_SDK_VERSION}.zip \
        --check-integrity --checksum sha-256=${ANDROID_SDK_CHECKSUM} \
    && unzip -q sdk-tools-linux-${ANDROID_SDK_VERSION}.zip \
    && rm sdk-tools-linux-${ANDROID_SDK_VERSION}.zip \
    && mkdir -p "${ANDROID_HOME}/licenses" \
    && echo -e "\nd56f5187479451eabf01fb78af6dfcb131a6481e" \
        > "${ANDROID_HOME}/licenses/android-sdk-license" \
    && ${ANDROID_HOME}/tools/bin/sdkmanager "build-tools;${ANDROID_BUILD_TOOLS_VERSION}" \
    && mv ${ANDROID_HOME}/build-tools/${ANDROID_BUILD_TOOLS_VERSION}/zipalign /usr/local/bin/ \
    && mv ${ANDROID_HOME}/build-tools/${ANDROID_BUILD_TOOLS_VERSION}/lib64/libc++.so /usr/local/lib64/ \
    && rm -rf /opt/android-sdk \
    && dnf remove -y aria2 java-1.8.0-openjdk unzip \
    && dnf clean all

# Install vdexExtractor
ARG VDEXEXTRACTOR_COMMIT=ff95073dba8eb44e86bdd8486f040a89f78193b8

RUN cd /tmp \
    && dnf install -y gcc git make zlib-devel \
    && git clone https://github.com/chenxiaolong/vdexExtractor.git \
    && pushd vdexExtractor \
    && git checkout ${VDEXEXTRACTOR_COMMIT} \
    && make -C src \
    && mv bin/vdexExtractor /usr/local/bin/ \
    && popd \
    && rm -rf vdexExtractor \
    && dnf remove -y gcc git make zlib-devel \
    && dnf clean all

# Volumes
ENV SYSROOT /sysroot
WORKDIR ${SYSROOT}

# Entrypoint
ADD docker/entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]

# Deodexer
ADD deodexer.py /usr/local/bin/deodexer
CMD ["deodexer", "."]
