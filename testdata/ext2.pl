#!/usr/bin/perl
use strict;
use warnings;
use open ':std', ':utf8';
use JSON ();
use File::Find ();
$| = 1;

{
    package Fedora::Review::Test;

    sub new {
        my $class = shift;
        my $self = {@_};
        bless $self, $class;
        return $self;
    }

    sub AUTOLOAD {
        my $self = shift;
        my ($prop) = (our $AUTOLOAD) =~ /^.*::(\w+)$/o;
        $self->{$prop} = shift if @_;
        return $self->{$prop};
    }
}

# Read and decode JSON input
sub getjson {
    my $json;
    while (<>) {
        last if /^$/;
        $json.= $_
    }
    return JSON::decode_json($json);
}

my $data = getjson;

# See if this could be a Perl package
my $perlpkg = 0;
File::Find::find(
    sub {
        if (/\.p[lm]$/so) {
            $perlpkg = 1;
            return
        }
    }, $data->{build_dir});
exit unless $perlpkg;

my @results = ();
my $test;
my %common = (
    url => 'https://fedoraproject.org/wiki/Packaging:Perl',
    group => 'Perl',
    deprecates => [],
    result => 'fail',
    type => 'MUST');

# Read in the spec file
my $spec = '';
open my $fh, '<', $data->{spec}->{path}
    or die "Cannot open ".$data->{spec}->{path}.": $!";
{
    local $/ = '';
    $spec = <$fh>
}
close $fh;

# Sample MODULE_COMPAT test
$test = Fedora::Review::Test->new(
    name => 'Perl MODULE_COMPAT test',
    text => 'Package requires Perl MODULE_COMPAT properly',
    output_extra => 'A result of an example test in Perl',
    url => $common{url}.'#Versioned_MODULE_COMPAT_Requires',
    %common);
$test->result('pass')
    if $spec
    =~ /Requires:
        \s*perl\(:MODULE_COMPAT_%\(eval\s+"`\%{__perl}\s+-V:version`";
        \s*echo\s+\$version\)\)/xs;
push @results, {%$test};

# Sample vendor(lib|arch) test
$test = Fedora::Review::Test->new(
    name => 'Use vendor paths',
    text => 'Perl package installs its files into vendor directories',
    output_extra => '',
    %common);
print JSON::encode_json({
    supported_api => 1,
    command => 'get_section',
    section => 'files'}), "\n";
$data = getjson;
$test->result('pass')
    if $data->{text} =~ /\%{perl_vendor(lib|arch)}/so;
push @results, {%$test};

print JSON::encode_json({
    supported_api => 1,
    command => 'results',
    checks => [@results]});
