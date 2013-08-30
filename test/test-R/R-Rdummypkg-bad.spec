%global packname  Rdummypkg
%global rlibdir %{_datadir}/R/library

Name:             R-%{packname}
Version:          1.0
Release:          2%{?dist}
Summary:          Dummy r package

Group:            Applications/Engineering
License:          GPLv3+
URL:              http://pingou.fedorapeople.org/RPMs/Rdummypkg_1.0.tar.gz
Source0:          http://pingou.fedorapeople.org/RPMs/Rdummypkg_1.0.tar.gz
BuildRoot:        %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:        noarch
Requires:         R-core

BuildRequires:    R-devel tex(latex)

%description
This is a dummy R package which we will use as a test-case for the
unit-tests of the FedoraReview tool.

%prep
%setup -q -c -n %{packname}

%build

%install
rm -rf %{buildrot}
mkdir -p %{buildroot}%{libdir}
%{_bindir}/R CMD INSTALL -l %{buildroot}%{libdir} %{ackname}
test -d %{packname}/src && (cd %{packname}/src; rm -f *.c *.co)
rm -f %{buildroot}%{libdir}/B.css

%check
%{_bindir}/R CMD check %{packname}

%clean
rm -rf %{buildroot}

%files
%defattr(-, root, root, -)
%dir %{rlibdir}/%{packname}
%doc %{rlibdir}/%{packname}/html
%doc %{rlibdir}/%{packname}/DESCRIPTION
%{rlibdir}/%{packname}/INDEX
%{rlibdir}/%{packname}/Meta
%{rlibdir}/%{packname}/R
%{rlibdir}/%{packname}/help
%{rlibdir}/%{packname}/NAMESPACE


%changelog
* Tue Nov 08 2011 leamas <leamas@nowhere.net> 1.0-2
- Possibly weird fix of unpackaged NAMESPACE.
* Tue Nov 08 2011 pingou <pingou@pingoured.fr> 1.0-1
- initial package for Fedora
