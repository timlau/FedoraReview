package RPM::Specfile;

use POSIX;

use strict;

use vars qw/$VERSION/;

$VERSION = '1.51';

sub new {
  my $class = shift;

  my $self = bless { }, $class;

  return $self;
}

my @simple_accessors =
  qw(
     build buildarch buildrequires buildroot check clean description distribution
     epoch file_param group install license macros name packager post postun
     pre preun prep release requires summary url vendor version
    );

foreach my $field (@simple_accessors) {
  my $sub = q {
    sub RPM::Specfile::[[field]] {
      my $self = shift;
      if (@_) {
        my $value = shift;
        $self->{__[[field]]__} = $value;
      }
      return $self->{__[[field]]__};
    }
  };

  $sub =~ s/\[\[field\]\]/$field/g;
  eval $sub;

  if ($@) {
    die $@;
  }
}

my @array_accessors = qw/source patch changelog provide require file buildrequire prefix/;

foreach my $field (@array_accessors) {
  my $sub = q {
    sub RPM::Specfile::[[field]] {
      my $self = shift;
      $self->{__[[field]]__} ||= [ ];

      if (@_) {
        my $index = shift;
        if (@_) {
          my $value = shift;
          $self->{__[[field]]__}->[$index] = $value;
        }
        return $self->{__[[field]]__}->[$index];
      }
      else {
        return @{$self->{__[[field]]__}};
      }
    }

    sub RPM::Specfile::push_[[field]] {
      my $self = shift;
      my $entry = shift;

      $self->{__[[field]]__} ||= [ ];
      push @{$self->{__[[field]]__}}, $entry;
    }

    sub RPM::Specfile::clear_[[field]] {
      my $self = shift;
      my $entry = shift;

      $self->{__[[field]]__} = [ ];
    }

  };

  $sub =~ s/\[\[field\]\]/$field/g;
  eval $sub;

  if ($@) {
    die $@;
  }
}


sub add_changelog_entry {
  my $self = shift;
  my $who = shift;
  my $entry = shift;
  my $version = shift;

  POSIX::setlocale( &POSIX::LC_ALL, "C" );

  my $output;
  $output .= strftime("* %a %b %d %Y $who", localtime time);
  $output .= " - $version" if $version;
  $output .= "\n- $entry\n";

  $self->push_changelog($output);
}

sub generate_specfile {
  my $self = shift;

  my $output;

  my %defaults =
    ( buildroot => "%{_tmppath}/%{name}-%{version}-%{release}-root" );
  $self->$_($self->$_() || $defaults{$_}) foreach keys %defaults;

  my %proper_names = ( url           => 'URL',
                       buildroot     => 'BuildRoot',
                       buildrequires => 'BuildRequires',
                       buildarch     => 'BuildArch',
                     );

  #
  # Add any macro definitions to the begining.
  $output .= $self->macros() . "\n" if defined $self->macros();

  foreach my $tag (qw/summary name version release epoch packager vendor distribution license group url buildroot buildarch/) {
    my $proper = $proper_names{$tag} || ucfirst $tag;

    next unless defined $self->$tag();
    $output .= "$proper: " . $self->$tag() . "\n";
  }

  my $req_format = sub {
    my $req = shift;
    my $ver = shift;

    if (ref $req) {
      ($req, $ver) = @$req;
    }

    if (defined $ver and $ver != 0) {
      return "$req >= $ver";
    }
    else {
      return "$req";
    }
  };

  foreach my $tag (qw/requires buildrequires/) {
    my $proper = $proper_names{$tag} || ucfirst $tag;

    next unless defined $self->$tag();

    $output .= "$proper: " . $req_format->($self->$tag) . "\n";
  }

  my @reqs = $self->buildrequire;
  for my $i (0 .. $#reqs) {
    $output .= "BuildRequires: " . $req_format->($reqs[$i]) . "\n";
  }

  @reqs = $self->require;
  for my $i (0 .. $#reqs) {
    $output .= "Requires: " . $req_format->($reqs[$i]) .  "\n";
  }

  my @sources = $self->source;
  for my $i (0 .. $#sources) {
    $output .= "Source$i: $sources[$i]\n";
  }

  my @patches = $self->patch;
  for my $i (0 .. $#patches) {
    $output .= "Patch$i: $patches[$i]\n";
  }

  #
  # Add any prefixes:
  my @prefixes = $self->prefix;
  for my $i (0 .. $#prefixes) {
    $output .= "Prefix: $prefixes[$i]\n";
  }
  $output .= "\n";

  #
  # Add patch entries to the %prep section if they exist:
  my $prep = $self->prep();
  for my $i (0 .. $#patches) {
    $prep .= "\n" if($i == 0);		# Just in case they did not add a newline
    $prep .= "%patch${i} -p1\n";
  }
  $self->prep($prep) if(defined($prep));

  if ($self->check) {
    my $build = $self->build;

    my ($cond, $body) = (undef, $self->check);
    if (ref $body) {
      $cond = $body->[0];
      $body = $body->[1];
    }

    $build .= "\n%check";
    if ($cond) {
      $build .= " $cond";
    }
    $build .= "\n$body\n";

    $self->build($build);
  }

  foreach my $sect (qw/description prep build install clean pre post preun postun/) {
    next if(!defined($self->$sect()));
    $output .= "%$sect\n";
    my $content = $self->$sect();
    # remove leading and trailing whitespace and spurious linefeeds
    $content =~ s/^\s*\n*//s;
    $content =~ s/[\s\n]*$/\n\n/s;
    $output .= $content;
  }

  if ($self->file_param) {
    $output .= "%files " . $self->file_param . "\n";
  }
  else {
    $output .= "%files\n";
  }
  $output .= "$_\n" foreach $self->file;

  $output .= "\n%changelog\n";
  $output .= "$_\n" foreach $self->changelog;

  return $output;
}

sub write_specfile {
  my $self = shift;
  my $dest = shift;

  open FH, ">$dest"
    or die "Can't open $dest: $!";

  print FH $self->generate_specfile;

  close FH;
}

1;

__END__
# Below is stub documentation for your module. You better edit it!
# TODO: yes, I better edit this better.

=head1 NAME

RPM::Specfile - Perl extension for creating RPM Specfiles

=head1 SYNOPSIS

  use RPM::Specfile;

=head1 DESCRIPTION

This is a simple module for creation of RPM Spec files.  Most of the methods in this
module are the same name as the RPM Spec file element they represent but in lower
case.  Furthermore the the methods are divided into two groups:

=over 4

=item Simple Accessors

These methods have the have the exact name as the element they represent (in lower
case).  If passed no arguments return a scalar representing the element.  If
an argument is passed they will set the value of the element.

=item List Accessors

These methods manipulate items in the spec file that are lists (e.g. the list of
patches maintained by the spec file).  Each element that is represented by a list
accessor will have at least three methods associated with it.

=over 8

=item *

A method to directly manipulate individual members of the list.  These methods
take as a first argument the index into the list, and as a second argument
the element value.  If no arguments are given it simply returns the list.
If only the index is given it returns the list member at that index.  If
the value is also given it will set the list member associated with the index.

=item *

A method to push a member onto the list.  Each of these methods have C<push_>
at the begining of their name.

=item *

A method to clear the list.  Each of these methods have C<clear_>
at the begining of their name.

=back

=back

=head1 RPM SPEC FILE ORGANIZATION

This section describes the basic structure of an RPM Spec file and how that
applies to RPM::Specfile.  It does not attempt to give a full description of
RPM Spec file syntax.

RPM Spec files are divided into the following sections:

=over 4

=item Preamble

This is where the meta information for the rpm is stored, such as its name version and
description.  Also, macro definitions are generally put at the top of the preamble.
The methods that are used to create this section are listed below:

	buildarch(), buildrequire(), buildrequires(), buildroot(),
	clear_buildrequire(), clear_changelog(), clear_patch(), clear_prefix(),
	clear_provide(), clear_require(), clear_source(), description(), distribution(),
	epoch(), group(), license(), macros(), name(), packager(), patch(), prefix(),
	provide(), push_buildrequire(), push_patch(), push_prefix(), push_provide(),
	push_require(), push_source(), release(), require(), requires(), source(),
	summary(), url(), vendor(), version()
	
Many of the elements of the Preamble are required.  See Maximum RPM for documentation
on which one are required and which ones are not.

=item Build Scriptlets

When rpms are built the install scriptlets are invoked.  These install
scriptlets are %prep, %build, %install, and %clean.  The contents of these
scripts can be set with the following methods:

	build(), clean(), install(), prep()

The %prep, %build, and %install scriptlets are required, but may be
null.

=item Install/Erase Scriplets

When an RPM is installed or erased various scriplets may be invoked.
These scriplets can be set via the following methods:

	post(), postun(), pre(), preun()

The install scriptlets are not required.

=item Files

The %files section is used to define what files should be delivered to the
system.  It further defines what the permsisions and ownership of the files
should be.  The methods that work with the %files sections are:

	file(), push_file(), clear_file(), file_param()

Note, a files section is required, but it may contain no entries.

=item Change Log

The last section in the spec file is the change log.  Methods to modify this are:

	add_changelog_entry(), changelog(), push_changelog(), clear_changelog()

=back

=head2 EXPORT

None by default.

=head1 METHODS

=item build

Not sure what this one does.

=item buildarch([$arch])

Returns the build arch.  If $arch is given will set build arch to $arch.

	$spec->buildarch('noarch');

=item buildrequire([$index, $requirement])

Returns a list of build requirement entries.  If $index and $requirement are provided,
it will set the entry referenced by $index to $requirement.

	@buildRequires = $spec->buildrequire();

=item buildrequires([$requirement])

Returns the build requires.  If $requirement is given, will set build requires line
to $requirement.

	$spec->buildrequires('noarch');

=item buildroot([$root])

Returns the build root (this is where rpm will build the package).  If $root is
given, will set the build root to $root.

	$spec->buildroot('/tmp/%{name}-%{version}-%{release}');

=item clean([$scriptlet])

Returns the %clean scriptlet.  If $scriptlet is given, will make the contents
of $scriptlet the %clean scriptlet.

	$spec->clean('rm -rf $RPM_BUILD_ROOT');

=item changelog([$index, $entry])

Returns a list of changelog entries.  If $index and $entry are provided it will
set the entry referenced by $index to $entry.

	@entries = $spec->changelog();

=item clear_buildrequire()

Clears the build requirement list.

	$spec->clear_buildrequire();

=item clear_changelog()

Clears the list of changelog entries.

	$spec->clear_changelog();

=item clear_file()

Clears the file list.

	$spec->clear_file();

=item clear_patch()

Clears the patch list.

	$spec->clear_patch();

=item clear_prefix()

Clears the prefix list.

	$spec->clear_prefix();

=item clear_provide()

Clears the list of provisions.

	$spec->clear_provide();

=item clear_require()

Clears the requirements list.

	$spec->clear_require();

=item clear_source()

Clears the list of sources.

	$spec->clear_source();

=item description([$desc])

Returns the description of the rpm.  If $desc is given, sets the description of the rpm.

	$spec->description('An automatically generated RPM');

=item distribution([$distro])

Returns the distribution of the rpm.  If $distro is given, sets the distribution
of the rpm.

	$spec->distribution('RedHat');

=item epoch([$epoch])

Returns the epoch of the rpm.  If $epoch is given sets the epoch of the rpm to $epoch.

	$spec->epoch('0');

=item file([$index, $file])

Returns a list of %file entries.  If $index and $file are provided, it will
set the entry referenced by $index to $file.

	@files = $spec->file();

=item file_param([$param])

Returns the parameters to add to the %files macro invocation.  If $param is given,
$param will be appended to the %files macro.

	$spec->file_param('-f file_list');

=item group([$group])

Returns the group in which the rpm belongs.  If $group is given, group will be set
to $group.

	$spec->group("Development/Libraries");

=item install([$scriptlet])

Returns the %install scriptlet.  If $scriptlet is given, the %install scriptlet
will be set to this.

	$spec->group('mkdir -p $RPM_BUILD_ROOT/usr/local/mypkg');

=item license([$license])

Returns the type of license the rpm is will be released under.  If $license is
given, license will be set to $license.


=item macros([$macro_defs])

Returns the macro definitions that are before the preamble of the specfile.
If $macro_defs is given, the macro definitions will be set to it.

	$spec->macros("%define x 1\n%define y 2");

=item name([$name])

Returns the name of the rpm.  If $name is given, the name is set to $name.

	$spec->name('perl-RPM-Specfile');

=item packager([$packager])

Returns the email address of the packager.  If $packager is set, packager is set to
$packager.

	$spec->packager('someone@some.where');

=item patch([$index, $patch])

Returns a list of patches.  If $index and $patch are provided it will
set the entry referenced by $index to $patch.

	@patches = $spec->patch();

=item post([$scriptlet])

Returns the contents of the %post scriptlet.  If $scriptlet is given, %post is set
to the value of $scriptlet.

	$spec->post("echo Running %%post...\nexit 0");

=item postun([$scriptlet])

Returns the contents of the %postun scriptlet.  If $scriptlet is given, %postun is set
to the value of $scriptlet.

	$spec->postun("echo Running %%postun...\nexit 0");

=item pre([$scriptlet])

Returns the contents of the %pre scriptlet.  If $scriptlet is given, %pre is set
to the value of $scriptlet.

	$spec->pre("echo Running %%pre...\nexit 0");

=item prefix([$index, $prefix])

Returns a list of prefix/relocation entries.  If $index and $prefix are provided it will
set the entry referenced by $index to $prefix.

	@prefixes = $spec->prefix();

=item preun([$scriptlet])

Returns the contents of the %preun scriptlet.  If $scriptlet is given, %preun is set
to the value of $scriptlet.

	$spec->preun("echo Running %%preun...\nexit 0");

=item prep([$scriptlet])

Returns the contents of the %prep scriptlet.  If $scriptlet is given, %prep is set
to the value of $scriptlet.

	$spec->prep("echo Running %%prep...\nexit 0");

=item provide([$index, $provision])

Returns a list of provision entries.  If $index and $provision are provided it will
set the entry referenced by $index to $provision.

	@provides = $spec->provide();

=item push_buildrequire([$entry])

Push a build requirement onto the list of build requirments.

	$spec->push_buildrequire('gcc >= 3.2');

=item push_changelog([$entry])

Pushes a changelog entry onto the list of changelog entries.

=item push_file([$entry])

Pushes a file onto the list of files.

	$spec->push_file('%attr(0664, root, root) %dir /usr/local/mypkg');
	$spec->push_file('%attr(0664, root, root) /usr/local/mypkg/myfile');

=item push_patch([$entry])

Pushes a patch onto the list of patches.

	$spec->push_patch('autorollback.patch');

Note, adding a patch implicitly adds entries to the %prep script.

=item push_prefix([$prefix])

Push a prefix onto to the list of valid relocations.

	$spec->clear_prefix('/usr/local/mypkg');

=item push_provide([$entry])

Pushes a provision onto the list of provisions.

	$spec->push_provide('kernel-tools = 2.6');

=item push_require([$entry])

Pushes a requirement onto the list of requirements.

	$spec->push_require('perl(RPM::Specfile)');

=item push_source([$entry])

Pushes a source entry onto the list of sources.

	$spec->push_source('wget-1.8.2.tar.gz');

=item release([$release])

Returns the release of the rpm.  If $release is specified, release is set to $release.

	$spec->release('1.1');

=item require([$index, $requirement])

Returns a list of requirement entries.  If $index and $requirement are provided it will
set the entry referenced by $index to $requirement.

	@requires = $spec->require();

=item requires([$requires])

Returns the value of the Requires line.  If $requires is set, the Requires line will
be set to $requires.

	$spec->requires('xdelta > 0:1.1.3-11, vlock > 0:1.3-13');

=item source([$index, $source])

Returns a list of source entries.  If $index and $source are provided it will
set the entry referenced by $index to $source.

	@sources = $spec->source();

=item summary([$summary])

Returns the value of the Summary line.  If $summary is set, the Summary line will
be set to $summary.

=item url([$url])

Returns the url of the rpm.  If $usr is set, the url is set to $url.

	$spec->url('http://www.cpan.org');

=item vendor([$vendor])

Returns the vendor of the rpm.  If $vendor is set, the vendor is set to $vendor.

	$spec->vendor('Perfect Distro, Inc.');

=item version([$version])

Returns the version of the rpm.  If $version is set, the version is set to $version.

=item new

Constructor of an RPM::Specfile object.

	$spec = RPM::Specfile->new();

=item add_changelog_entry($who, $entry, $version)

Adds an entry to the change log.  $who should be set to something like:

	your name<your_email@somewhere.com>

$entry is the list of changes, and $version is the version to which the change
log applies.

	$spec->add_changelog('John Smith <jsmith@smiths.com>',
		'- Added a great bit of functionality',
		'1.0');

This method will automatically generate the time of the entry.

=item generate_specfile()

Generates the specfile and returns it as a scalar.

=item write_specfile($file)

Writes specfile to $file.

=head1 NOTE

A good example of the use of RPM::Specfile is cpanflute2 which comes with the
RPM::Specfile cpan archive.

=head1 AUTHOR

Chip Turner <cturner@pattern.net>

=head1 LICENSE

This module is distributed under the same terms as Perl itself:

http://dev.perl.org/licenses/

=head1 SEE ALSO

L<perl>
cpanflute2
Maximum RPM (http://www.rpm.org/max-rpm/)

=cut
