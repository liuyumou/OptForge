//! Contiguous work partitions: numerical term and reduction order never change.
use std::ops::Range;

pub(crate) fn uniform(count: usize, workers: usize) -> Vec<Range<usize>> {
    let width = if count < 4096 { 1 } else { workers };
    (0..width)
        .map(|w| count * w / width..count * (w + 1) / width)
        .collect()
}

pub(crate) fn sparse(offsets: &[usize], workers: usize) -> Vec<Range<usize>> {
    let count = offsets.len() - 1;
    let work = offsets[count] + count;
    if work < 16384 || workers == 1 || count < 2 {
        return std::iter::once(0..count).collect();
    }
    let width = workers.min(count);
    let mut boundaries = vec![0];
    for w in 1..width {
        let target = work * w / width;
        // A column/row stays whole. Binary search costs O(workers * log(lines)).
        let mut lo = *boundaries.last().unwrap();
        let mut hi = count;
        while lo < hi {
            let mid = lo + (hi - lo) / 2;
            if offsets[mid] + mid < target {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        boundaries.push(lo);
    }
    boundaries.push(count);
    boundaries.windows(2).map(|b| b[0]..b[1]).collect()
}

/// Use the direct weighted path only where the old column-count policy leaves
/// work serial or a uniform partition has more than 1.5 times average work.
pub(crate) fn weighted_columns(offsets: &[usize], workers: usize) -> bool {
    let count = offsets.len() - 1;
    let work = offsets[count] + count;
    if workers == 1 || count < 2 || work < 16384 {
        return false;
    }
    if count < 4096 {
        return true;
    }
    let maximum = (0..workers)
        .map(|w| {
            let start = count * w / workers;
            let end = count * (w + 1) / workers;
            offsets[end] - offsets[start] + end - start
        })
        .max()
        .unwrap_or(0);
    2 * maximum * workers > 3 * work
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn scheduler_uses_work_and_keeps_balanced_staging() {
        let balanced: Vec<_> = (0..=8192).map(|i| i * 128).collect();
        assert!(!weighted_columns(&balanced, 4));
        let heavy: Vec<_> = (0..=257).map(|i| i * 4096).collect();
        assert!(weighted_columns(&heavy, 4));
        let skew: Vec<_> = (0..=8192)
            .map(|i| {
                if i <= 256 {
                    i * 4096
                } else {
                    256 * 4096 + i - 256
                }
            })
            .collect();
        assert!(weighted_columns(&skew, 4));
        assert!(!weighted_columns(&skew, 1));
    }
    #[test]
    fn few_heavy_columns_use_all_workers_and_preserve_order() {
        let offsets: Vec<_> = (0..=257).map(|i| i * 4096).collect();
        for workers in [1, 3, 4] {
            let ranges = sparse(&offsets, workers);
            assert_eq!(ranges.len(), workers);
            assert_eq!(
                ranges.iter().flat_map(Clone::clone).collect::<Vec<_>>(),
                (0..257).collect::<Vec<_>>()
            );
            assert!(ranges.iter().all(|r| r.len() <= 257usize.div_ceil(workers)));
        }
    }
    #[test]
    fn skewed_and_empty_lines_have_no_gaps_or_duplicates() {
        for n in [0, 1, 7, 4097] {
            let offsets: Vec<_> = (0..=n)
                .map(|i| if i == 0 { 0 } else { 100000 + i })
                .collect();
            for workers in [1, 3, 4] {
                let ranges = sparse(&offsets, workers);
                assert_eq!(
                    ranges.iter().flat_map(Clone::clone).collect::<Vec<_>>(),
                    (0..n).collect::<Vec<_>>()
                );
                assert!(ranges.len() <= workers);
            }
        }
    }
}
