// A verified integer maximum utility: the result is one of the inputs and
// is greater than or equal to both.

function Max(a: int, b: int): int
  ensures Max(a, b) == a || Max(a, b) == b
  ensures Max(a, b) >= a && Max(a, b) >= b
{
  if a >= b then a else b
}

method TestMax(a: int, b: int)
lemma MaxCommutative(a: int, b: int)
 ensures Max(a, b) == Max(b, a)
{
 if a >= b {
   assert Max(a, b) == a;
   if b >= a {
     assert a == b;
     assert Max(b, a) == b;
   } else {
     assert Max(b, a) == a;
   }
 } else {
   assert Max(a, b) == b;
   assert Max(b, a) == b;
 }
}

method TestMaxAlgebra(a: int, b: int, c: int)
{
 MaxCommutative(a, b);
 assert Max(a, b) == Max(b, a);
 assert Max(a, a) == a;
 assert Max(Max(a, b), c) == Max(a, Max(b, c));
}

{
  var result := Max(a, b);
  assert result == a || result == b;
  assert result >= a && result >= b;
}
