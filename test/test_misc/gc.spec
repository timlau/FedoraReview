
Summary: A garbage collector for C and C++
Name:    gc
%global base_ver 7.2
Version: 7.2c
Release: 3%{?dist}

Group:   System Environment/Libraries
License: BSD
Url:     http://www.hpl.hp.com/personal/Hans_Boehm/gc/
Source0: http://www.hpl.hp.com/personal/Hans_Boehm/gc/gc_source/gc-%{version}%{?pre}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

## upstreamable patches

## upstream patches

BuildRequires: automake libtool
BuildRequires: pkgconfig

# rpmforge compatibility
Obsoletes: libgc < %{version}-%{release}
Provides:  libgc = %{version}-%{release}

%description
The Boehm-Demers-Weiser conservative garbage collector can be
used as a garbage collecting replacement for C malloc or C++ new.

%package devel
Summary: Libraries and header files for %{name} development
Group:   Development/Libraries
Requires: %{name}%{?_isa} = %{version}-%{release}
Obsoletes: libgc-devel < %{version}-%{release}
Provides:  libgc-devel = %{version}-%{release}
%description devel
%{summary}.

%package -n libatomic_ops-devel
Summary:   Atomic memory update operations
Group:     Development/Libraries
# libatomic_ops.a is MIT
# libatomic_ops_gpl.a is GPLv2+
License:   MIT and GPLv2+
Provides:  libatomic_ops-static = %{version}-%{release}
%description -n libatomic_ops-devel
Provides implementations for atomic memory update operations on a
number of architectures. This allows direct use of these in reasonably
portable code. Unlike earlier similar packages, this one explicitly
considers memory barrier semantics, and allows the construction of code
that involves minimum overhead across a variety of architectures.


%prep
%setup -q -n gc-%{base_ver}%{?pre}

# refresh auto*/libtool to purge rpaths
rm -f libtool libtool.m4
autoreconf -i -f


%build

# see bugzilla.redhat.com/689877
CPPFLAGS="-DUSE_GET_STACKBASE_FOR_MAIN"; export CPPFLAGS

%configure \
  --disable-dependency-tracking \
  --disable-static \
  --enable-cplusplus \
  --enable-large-config \
%ifarch %{ix86}
  --enable-parallel-mark \
%endif
  --enable-threads=posix \
  --with-libatomic-ops=no

make %{?_smp_mflags}
make %{?_smp_mflags} -C libatomic_ops


%install
rm -rf %{buildroot}

make install DESTDIR=%{buildroot}
make install DESTDIR=%{buildroot} -C libatomic_ops

install -p -D -m644 doc/gc.man	%{buildroot}%{_mandir}/man3/gc.3

## Unpackaged files
rm -rfv %{buildroot}%{_datadir}/gc/
rm -rfv %{buildroot}%{_datadir}/libatomic_ops/{COPYING,*.txt}
rm -fv  %{buildroot}%{_libdir}/lib*.la


%check
make check
make check -C libatomic_ops ||:


%clean
rm -rf %{buildroot}


%post   -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%defattr(-,root,root,-)
%doc doc/README
%doc doc/README.changes doc/README.contributors
%doc doc/README.environment doc/README.linux
%{_libdir}/libcord.so.1*
%{_libdir}/libgc.so.1*
%{_libdir}/libgccpp.so.1*

%files devel
%defattr(-,root,root,-)
%doc doc/*.html
%{_includedir}/gc.h
%{_includedir}/gc_cpp.h
%{_includedir}/gc/
%{_libdir}/libcord.so
%{_libdir}/libgc.so
%{_libdir}/libgccpp.so
%{_libdir}/pkgconfig/bdw-gc.pc
%{_mandir}/man3/gc.3*

%files -n libatomic_ops-devel
%defattr(-,root,root,-)
%doc libatomic_ops/AUTHORS libatomic_ops/ChangeLog libatomic_ops/COPYING libatomic_ops/NEWS libatomic_ops/README
%doc libatomic_ops/doc/*.txt
%{_includedir}/atomic_ops.h
%{_includedir}/atomic_ops/
%{_libdir}/libatomic_ops.a
%{_libdir}/pkgconfig/atomic_ops.pc
# GPLv2+ bits
%{_includedir}/atomic_ops_malloc.h
%{_includedir}/atomic_ops_stack.h
%{_libdir}/libatomic_ops_gpl.a


%changelog
* Fri Jul 27 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 7.2c-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jul 24 2012 Rex Dieter <rdieter@fedoraproject.org> 7.2c-2
- rebuild

* Tue Jun 26 2012 Rex Dieter <rdieter@fedoraproject.org> 7.2c-1
- 7.2c

* Fri Jun 15 2012 Rex Dieter <rdieter@fedoraproject.org>
- 7.2b-2
- backport patches from gc-7_2-hotfix-2 branch in lieu of 7.2c release
- gc 7.2 final abi broken when changing several symbols to hidden (#825473)
- CVE-2012-2673 gc: malloc() and calloc() overflows (#828878)

* Wed May 30 2012 Rex Dieter <rdieter@fedoraproject.org> 7.2b-1
- gc-7.2b

* Mon May 14 2012 Rex Dieter <rdieter@fedoraproject.org>
- 7.2-1
- gc-7.2 (final)

* Fri Mar 02 2012 Rex Dieter <rdieter@fedoraproject.org> 7.2-0.7.alpha6
- libatomic_ops: use -DAO_USE_PTHREAD_DEFS on ARMv5

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 7.2-0.6.alpha6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Wed Oct 26 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 7.2-0.5.alpha6
- Rebuilt for glibc bug#747377

* Mon Jun 20 2011 Rex Dieter <rdieter@fedoraproject.rog> 7.2-0.4.alpha6.20110107
- gc-7.2alpha6
- build with -DUSE_GET_STACKBASE_FOR_MAIN (#689877)

* Wed Feb 09 2011 Rex Dieter <rdieter@fedoraproject.org> 7.2-0.3.alpha5.20110107
- bdwgc-7.2alpha4 20110107 snapshot

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 7.2-0.2.alpha4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Fri Dec 11 2009 Rex Dieter <rdieter@fedoraproject.org> - 7.2-0.1.alpha4
- gc-7.2alpha4
- use/package internal libatomic_ops

* Tue Dec  8 2009 Michael Schwendt <mschwendt@fedoraproject.org> - 7.1-10
- Explicitly BR libatomic_ops-static in accordance with the Packaging
  Guidelines (libatomic_ops-devel is still static-only).

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 7.1-9
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Jul 16 2009 Rex Dieter <rdieter@fedoraproject.org. - 7.1-8
- FTBFS gc-7.1-7.fc11 (#511365)

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 7.1-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Fri Dec 12 2008 Rex Dieter <rdieter@fedoraproject.org> 7.1-6
- rebuild for pkgconfig deps

* Wed Oct 15 2008 Rex Dieter <rdieter@fedoraproject.org> 7.1-5
- forward-port patches (gcinit, sparc)

* Fri Oct 03 2008 Rex Dieter <rdieter@fedoraproject.org> 7.1-4
- BR: libatomic_ops-devel

* Mon Sep 08 2008 Rex Dieter <rdieter@fedoraproject.org> 7.1-3
- upstream DONT_ADD_BYTE_AT_END patch
- spec cosmetics

* Sat Jul 12 2008 Rex Dieter <rdieter@fedoraproject.org> 7.1-2
- --enable-large-config (#453972)

* Sun May 04 2008 Rex Dieter <rdieter@fedoraproject.org> 7.1-1
- gc-7.1
- purge rpaths

* Fri Feb 08 2008 Rex Dieter <rdieter@fedoraproject.org> 7.0-7
- respin (gcc43)

* Wed Aug 29 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 7.0-6
- BR: gawk
- fixup compat_header patch to avoid needing auto* tools

* Wed Aug 29 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 7.0-5
- compat_header patch (supercedes previous pkgconfig patch)

* Tue Aug 21 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 7.0-4
- pkgconfig patch (cflags += -I%%_includedir/gc)

* Tue Aug 21 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 7.0-3
- respin (ppc32)

* Tue Jul 24 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 7.0-2
- gcinit patch, ABI compatibility (#248700)

* Mon Jul 09 2007 Rex Dieter <rdieter[AT]fedoraproject.org> 7.0-1
- gc-7.0

* Mon Dec 11 2006 Rex Dieter <rexdieter[AT]users.sf.net> 6.8-3
- Obsoletes/Provides: libgc(-devel) (rpmforge compatibility)

* Mon Aug 28 2006 Rex Dieter <rexdieter[AT]users.sf.net> 6.8-2
- fc6 respin

* Thu Jul 13 2006 Rex Dieter <rexdieter[AT]users.sf.net> 6.8-1
- 6.8

* Fri Mar 03 2006 Rex Dieter <rexdieter[AT]users.sf.net> 6.7-1
- 6.7

* Wed Mar 1 2006 Rex Dieter <rexdieter[AT]users.sf.net>
- fc5: gcc/glibc respin

* Fri Feb 10 2006 Rex Dieter <rexdieter[AT]users.sf.net> 6.6-5
- gcc(4.1) patch

* Thu Dec 01 2005 Rex Dieter <rexdieter[AT]users.sf.net> 6.6-4
- Provides: libgc(-devel)

* Wed Sep 14 2005 Rex Dieter <rexdieter[AT]users.sf.net> 6.6-3
- no-undefined patch, libtool madness (#166344)

* Mon Sep 12 2005 Rex Dieter <rexdieter[AT]users.sf.net> 6.6-2
- drop opendl patch (doesn't appear to be needed anymore)

* Fri Sep 09 2005 Rex Dieter <rexdieter[AT]users.sf.net> 6.6-1
- 6.6

* Wed May 25 2005 Rex Dieter <rexdieter[AT]users.sf.net> 6.5-1
- 6.5

* Thu Apr  7 2005 Michael Schwendt <mschwendt[AT]users.sf.net>
- rebuilt

* Wed Jan 26 2005 Rex Dieter <rexdieter[AT]users.sf.net> 0:6.4-2
- --enable-threads unconditionally
- --enable-parallel-mark only on %%ix86 (#144681)

* Mon Jan 10 2005 Rex Dieter <rexdieter[AT]users.sf.net> 0:6.4-1
- 6.4
- update opendl patch

* Fri Jul 09 2004 Rex Dieter <rexdieter at sf.net> 0:6.3-0.fdr.1
- 6.3(final)

* Tue Jun 01 2004 Rex Dieter <rexdieter at sf.net> 0:6.3-0.fdr.0.4.alpha6
- dlopen patch

* Wed May 26 2004 Rex Dieter <rexdieter at sf.net> 0:6.3-0.fdr.0.3.alpha6
- explictly --enable-threads ('n friends)

* Tue May 25 2004 Rex Dieter <rexdieter at sf.net> 0:6.3-0.fdr.0.2.alpha6
- 6.3alpha6
- --disable-static
- --enable-parallel-mark

* Wed Dec 17 2003 Rex Dieter <rexdieter at sf.net> 0:6.3-0.fdr.0.1.alpha2
- 6.3alpha2

* Thu Oct 02 2003 Rex Dieter <rexdieter at sf.net> 0:6.2-0.fdr.3
- OK, put manpage in man3.

* Thu Oct 02 2003 Rex Dieter <rexdieter at sf.net> 0:6.2-0.fdr.2
- drop manpage pending feedback from developer.

* Tue Sep 30 2003 Rex Dieter <rexdieter at sf.net> 0:6.2-0.fdr.1
- fix manpage location
- remove .la file (it appears unnecessary after all, thanks to opendl patch)
- remove cvs tag from description
- touchup -devel desc/summary.
- macro update to support Fedora Core

* Thu Sep 11 2003 Rex Dieter <rexdieter at sf.net> 0:6.2-0.fdr.0
- 6.2 release.
- update license (BSD)
- Consider building with: --enable-parallel-mark
  (for now, no).

