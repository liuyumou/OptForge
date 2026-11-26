// Minimal C declarations for the pinned, installed 64-bit GMP 6.2.1 ABI.
// No system package/header installation is needed. The build tool verifies the
// runtime digest and version, and admission exercises the rational operations.
#pragma once
#include <cstddef>
struct SpZ { int allocated; int size; unsigned long* limbs; };
struct SpQ { SpZ numerator; SpZ denominator; };
static_assert(sizeof(unsigned long)==8 && sizeof(SpZ)==16 && sizeof(SpQ)==32);
extern "C" {
extern const char* __gmp_version;
void __gmpq_init(SpQ*);
void __gmpq_clear(SpQ*);
void __gmpq_set(SpQ*,const SpQ*);
void __gmpq_set_si(SpQ*,long,unsigned long);
int __gmpq_set_str(SpQ*,const char*,int);
void __gmpq_canonicalize(SpQ*);
void __gmpq_add(SpQ*,const SpQ*,const SpQ*);
void __gmpq_sub(SpQ*,const SpQ*,const SpQ*);
void __gmpq_mul(SpQ*,const SpQ*,const SpQ*);
void __gmpq_div(SpQ*,const SpQ*,const SpQ*);
void __gmpq_neg(SpQ*,const SpQ*);
int __gmpq_cmp(const SpQ*,const SpQ*);
char* __gmpq_get_str(char*,int,const SpQ*);
std::size_t __gmpz_sizeinbase(const SpZ*,int);
}
