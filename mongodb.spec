%global         daemon mongod
Name:           mongodb
Version:        1.8.2
Release:        6%{?dist}
Summary:        High-performance, schema-free document-oriented database
Group:          Applications/Databases
License:        AGPLv3 and zlib and ASL 2.0
# util/md5 is under the zlib license
# manpages and bson are under ASL 2.0
# everything else is AGPLv3
URL:            http://www.mongodb.org

Source0:        http://fastdl.mongodb.org/src/%{name}-src-r%{version}.tar.gz
Source1:        %{daemon}.service
Source2:        %{daemon}.sysconf
Source3:        %{name}.logrotate
Source4:        %{name}.conf
Patch1:         mongodb-no-term.patch
Patch2:         mongodb-src-r1.8.2-js.patch

BuildRequires:  python-devel
BuildRequires:  scons
BuildRequires:  boost-devel
BuildRequires:  pcre-devel
BuildRequires:  js-devel
BuildRequires:  readline-devel
BuildRequires:  libpcap-devel
# to run tests
BuildRequires:  unittest

Requires(post): systemd-units
Requires(preun): systemd-units

Requires(pre):  shadow-utils

Requires(postun): systemd-units

Requires:       lib%{name} = %{version}-%{release}

# Mongodb must run on a little-endian CPU (see bug #630898)
ExcludeArch:    ppc ppc64 %{sparc} s390 s390x

%description
Mongo (from "humongous") is a high-performance, open source, schema-free
document-oriented database. MongoDB is written in C++ and offers the following
features:
    * Collection oriented storage: easy storage of object/JSON-style data
    * Dynamic queries
    * Full index support, including on inner objects and embedded arrays
    * Query profiling
    * Replication and fail-over support
    * Efficient storage of binary data including large objects (e.g. photos
    and videos)
    * Auto-sharding for cloud-level scalability (currently in early alpha)
    * Commercial Support Available

A key goal of MongoDB is to bridge the gap between key/value stores (which are
fast and highly scalable) and traditional RDBMS systems (which are deep in
functionality).

%package -n lib%{name}
Summary:        MongoDB shared libraries
Group:          Development/Libraries

%description -n lib%{name}
This package provides the shared library for the MongoDB client.

%package devel
Summary:        MongoDB header files
Group:          Development/Libraries
Requires:       lib%{name} = %{version}-%{release}
Requires:       boost-devel

%description devel
This package provides the header files and C++ driver for MongoDB. MongoDB is
a high-performance, open source, schema-free document-oriented database.

%package server
Summary:        MongoDB server, sharding server and support scripts
Group:          Applications/Databases
Requires:       %{name} = %{version}-%{release}

%description server
This package provides the mongo server software, mongo sharding server
software, default configuration files, and init scripts.


%prep
%setup -q -n mongodb-src-r%{version}
%patch1 -p1
%patch2 -p1

# spurious permissions
chmod -x README
chmod -x db/repl/rs_exception.h
chmod -x db/resource.h

# wrong end-of-file encoding
sed -i 's/\r//' db/repl/rs_exception.h
sed -i 's/\r//' db/resource.h
sed -i 's/\r//' README

%build
# Disable error on warning, use boost-fs 2
mv SConstruct SConstruct.orig
grep -v 'Werror' SConstruct.orig > SConstruct
sed -i 's/-Wall/-DBOOST_FILESYSTEM_VERSION=2/' SConstruct

scons %{?_smp_mflags} --sharedclient .

%install
rm -rf %{buildroot}
scons install . \
%if "%{dist}" == "el5"
	--extralib termcap \
%endif
	--sharedclient \
	--prefix=%{buildroot}%{_prefix} \
	--nostrip \
	--full
rm -f %{buildroot}%{_libdir}/libmongoclient.a

mkdir -p %{buildroot}%{_sharedstatedir}/%{name}
mkdir -p %{buildroot}%{_localstatedir}/log/%{name}
mkdir -p %{buildroot}/lib/systemd/system
mkdir -p %{buildroot}%{_sysconfdir}/sysconfig

install -p -D -m 644 %{SOURCE1} %{buildroot}/lib/systemd/system/%{daemon}.service
install -p -D -m 644 %{SOURCE2} %{buildroot}%{_sysconfdir}/sysconfig/%{daemon}
install -p -D -m 644 %{SOURCE3} %{buildroot}%{_sysconfdir}/logrotate.d/%{name}
install -p -D -m 644 %{SOURCE4} %{buildroot}%{_sysconfdir}/mongodb.conf

mkdir -p %{buildroot}%{_mandir}/man1
cp -p debian/*.1 %{buildroot}%{_mandir}/man1/

%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig

%pre server
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd %{name} >/dev/null || \
useradd -r -g %{name} -d %{_sharedstatedir}/%{name} -s /sbin/nologin \
-c "MongoDB Database Server" %{name}
exit 0

%post server
/bin/systemctl daemon-reload &> /dev/null || :


%preun server
if [ $1 = 0 ] ; then
   /bin/systemctl --no-reload disable %{daemon}.service &> /dev/null
   /bin/systemctl stop %{daemon}.service &> /dev/null
fi


%postun server
/bin/systemctl daemon-reload &> /dev/null
if [ "$1" -ge "1" ] ; then
   /bin/systemctl try-restart %{daemon}.service &> /dev/null
fi


%files
%{_bindir}/mongo
%{_bindir}/mongodump
%{_bindir}/mongoexport
%{_bindir}/mongofiles
%{_bindir}/mongoimport
%{_bindir}/mongorestore
%{_bindir}/mongostat
%{_bindir}/mongosniff
%{_bindir}/bsondump

%{_mandir}/man1/mongo.1*
%{_mandir}/man1/mongod.1*
%{_mandir}/man1/mongodump.1*
%{_mandir}/man1/mongoexport.1*
%{_mandir}/man1/mongofiles.1*
%{_mandir}/man1/mongoimport.1*
%{_mandir}/man1/mongosniff.1*
%{_mandir}/man1/mongostat.1*
%{_mandir}/man1/mongorestore.1*

%files -n lib%{name}
%doc README GNU-AGPL-3.0.txt APACHE-2.0.txt
%{_libdir}/libmongoclient.so

%files server
%{_bindir}/mongod
%{_bindir}/mongos
%{_mandir}/man1/mongod.1*
%{_mandir}/man1/mongos.1*
%dir %attr(0755, %{name}, root) %{_sharedstatedir}/%{name}
%dir %attr(0755, %{name}, root) %{_localstatedir}/log/%{name}
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}
%config(noreplace) %{_sysconfdir}/mongodb.conf
%config(noreplace) %{_sysconfdir}/sysconfig/%{daemon}
/lib/systemd/system/*.service

%files devel
%{_includedir}/mongo

%changelog
* Thu Jul 28 2011 Chris Lalancette <clalance@redhat.com> - 1.8.2-6
- BZ 725601 - fix the javascript engine to not hang (thanks to Eduardo Habkost)

* Mon Jul 25 2011 Chris Lalancette <clalance@redhat.com> - 1.8.2-5
- Fixes to post server, preun server, and postun server to use systemd

* Thu Jul 21 2011 Chris Lalancette <clalance@redhat.com> - 1.8.2-4
- Update to use systemd init

* Thu Jul 21 2011 Chris Lalancette <clalance@redhat.com> - 1.8.2-3
- Rebuild for boost ABI break

* Wed Jul 13 2011 Chris Lalancette <clalance@redhat.com> - 1.8.2-2
- Make mongodb-devel require boost-devel (BZ 703184)

* Fri Jul 01 2011 Chris Lalancette <clalance@redhat.com> - 1.8.2-1
- Update to upstream 1.8.2
- Add patch to ignore TERM

* Fri Jul 01 2011 Chris Lalancette <clalance@redhat.com> - 1.8.0-3
- Bump release to build against new boost package

* Sat Mar 19 2011 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.8.0-2
- Make mongod bind only to 127.0.0.1 by default

* Sat Mar 19 2011 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.8.0-1
- Update to 1.8.0
- Remove upstreamed nonce patch

* Wed Feb 16 2011 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.7.5-5
- Add nonce patch

* Sun Feb 13 2011 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.7.5-4
- Manually define to use boost-fs v2

* Sat Feb 12 2011 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.7.5-3
- Disable extra warnings

* Fri Feb 11 2011 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.7.5-2
- Disable compilation errors on warnings

* Fri Feb 11 2011 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.7.5-1
- Update to 1.7.5
- Remove CPPFLAGS override
- Added libmongodb package

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.6.4-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Mon Dec 06 2010 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.6.4-3
- Add post/postun ldconfig... oops!

* Mon Dec 06 2010 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.6.4-2
- Enable --sharedclient option, remove static lib

* Sat Dec 04 2010 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.6.4-1
- New upstream release

* Fri Oct 08 2010 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.6.3-4
- Put -fPIC onto both the build and install scons calls

* Fri Oct 08 2010 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.6.3-3
- Define _initddir when it doesn't exist for el5 and others

* Fri Oct 08 2010 Nathaniel McCallum <nathaniel@natemccallum.com> - 1.6.3-2
- Added -fPIC build option which was dropped by accident

* Thu Oct  7 2010 Ionuț C. Arțăriși <mapleoin@fedoraproject.org> - 1.6.3-1
- removed js Requires
- new upstream release
- added more excludearches: sparc s390, s390x and bugzilla pointer

* Tue Sep  7 2010 Ionuț C. Arțăriși <mapleoin@fedoraproject.org> - 1.6.2-2
- added ExcludeArch for ppc

* Fri Sep  3 2010 Ionuț C. Arțăriși <mapleoin@fedoraproject.org> - 1.6.2-1
- new upstream release 1.6.2
- send mongod the USR1 signal when doing logrotate
- use config options when starting the daemon from the initfile
- removed dbpath patch: rely on config
- added pid directory to config file and created the dir in the spec
- made the init script use options from the config file
- changed logpath in mongodb.conf

* Wed Sep  1 2010 Ionuț C. Arțăriși <mapleoin@fedoraproject.org> - 1.6.1-1
- new upstream release 1.6.1
- patched SConstruct to allow setting cppflags
- stopped using sed and chmod macros

* Fri Aug  6 2010 Ionuț C. Arțăriși <mapleoin@fedoraproject.org> - 1.6.0-1
- new upstream release: 1.6.0
- added -server package
- added new license file to %%docs
- fix spurious permissions and EOF encodings on some files

* Tue Jun 15 2010 Ionuț C. Arțăriși <mapleoin@fedoraproject.org> - 1.4.3-2
- added explicit js requirement
- changed some names

* Wed May 26 2010 Ionuț C. Arțăriși <mapleoin@fedoraproject.org> - 1.4.3-1
- updated to 1.4.3
- added zlib license for util/md5
- deleted upstream deb/rpm recipes
- made scons not strip binaries
- made naming more consistent in logfile, lockfiles, init scripts etc.
- included manpages and added corresponding license
- added mongodb.conf to sources

* Fri Oct  2 2009 Ionuț Arțăriși <mapleoin@fedoraproject.org> - 1.0.0-3
- fixed libpath issue for 64bit systems

* Thu Oct  1 2009 Ionuț Arțăriși <mapleoin@fedoraproject.org> - 1.0.0-2
- added virtual -static package

* Mon Aug 31 2009 Ionuț Arțăriși <mapleoin@fedoraproject.org> - 1.0.0-1
- Initial release.
