use strict; use warnings;
use JSON::XS;
my $j = JSON::XS->new->canonical(0);
my $s = "";
for my $x (0..9999) { $s = $j->encode({ a => [$x, 2, 3], b => "hello" }); }
print "$s\n";
