# Run from the repository root with Rscript tests/test_fluvial_r.R.
source("fluvial_seismology/scripts/processing/signal_spectrogram.R")
source("fluvial_seismology/scripts/processing/aux_clipspectrogram.R")

dt <- 0.01
samples <- 0:599
time <- as.POSIXct("2025-01-01", tz = "UTC") + samples * dt
signal <- sin(2 * pi * 12 * samples * dt)
estimate <- function(x, ...) {
  signal_spectrogram(x, time = time[seq_along(x)], dt = dt,
                     window = 1, overlap = 0, ...)
}

full <- estimate(signal)
one <- estimate(signal[1:100])
reference <- stats::spectrum(signal[1:100], method = "pgram", plot = FALSE)
stopifnot(
  identical(full$t, time[seq(1, 600, by = 100)]),
  identical(one$t, time[1]),
  isTRUE(all.equal(full$f, reference$freq / dt)),
  isTRUE(all.equal(unname(full$S[, 1]), 10 * log10(reference$spec)))
)

welch <- estimate(signal, Welch = TRUE, window_sub = 1)
stopifnot(isTRUE(all.equal(welch, full)))
mixed <- sin(2 * pi * 12 * samples * dt) * rep(c(1, 4), each = 50, length.out = 600)
welch_two <- estimate(mixed, Welch = TRUE, window_sub = 0.5, overlap_sub = 0)
reference_sub <- lapply(list(mixed[1:50], mixed[51:100]), function(x) {
  stats::spectrum(x, method = "pgram", plot = FALSE)
})
expected_power <- (reference_sub[[1]]$spec + reference_sub[[2]]$spec) / 2
stopifnot(
  isTRUE(all.equal(welch_two$f, reference_sub[[1]]$freq / dt)),
  isTRUE(all.equal(unname(welch_two$S[, 1]), 10 * log10(expected_power)))
)

masked_columns <- function(spec) unname(apply(is.na(spec$S), 2, all))
with_gaps <- signal
with_gaps[c(1:5, 160, 290:291, 596:600)] <- NA_real_
masked <- estimate(with_gaps)
expected_mask <- c(TRUE, TRUE, TRUE, FALSE, FALSE, TRUE)
stopifnot(
  identical(masked_columns(masked), expected_mask),
  identical(masked$S[, !expected_mask], full$S[, !expected_mask])
)

event <- structure(
  list(signal = with_gaps,
       meta = list(dt = dt, starttime = time[1], n = length(signal)),
       history = list()),
  class = "eseis"
)
event_result <- signal_spectrogram(event, window = 1, overlap = 0)
stopifnot(inherits(event_result, "eseis"),
          identical(event_result$PSD, masked))

bins <- matrix(1:12, nrow = 4)
band <- aux_clipspectrogram(bins, f = c(15, 18), res = 1, dt = dt)
stopifnot(identical(band$power, c(2, 6, 10)))

band_matrix <- aux_clipspectrogram(full$S, f = c(11.5, 12.1), res = 1, dt = dt)
band_object <- aux_clipspectrogram(full, f = c(11.5, 12.1), res = 1)
stopifnot(
  identical(band_matrix$power, as.numeric(full$S[full$f == 12, ])),
  identical(band_object$power, band_matrix$power),
  identical(band_object$time, full$t)
)
clipped <- aux_clipspectrogram(masked, f = c(10, 20), res = 11)
stopifnot(
  inherits(clipped, "spectrogram"),
  identical(clipped$t, masked$t),
  identical(clipped$f, seq(10, 20, length.out = 11)),
  identical(masked_columns(clipped), expected_mask)
)

ar_input <- signal
ar_input[1:100] <- NA_real_
ar <- estimate(ar_input, method = "autoregressive")
ar_reference <- stats::spectrum(signal[101:200], method = "ar", plot = FALSE)
stopifnot(
  identical(masked_columns(ar), c(TRUE, rep(FALSE, 5))),
  isTRUE(all.equal(ar$f, ar_reference$freq / dt)),
  isTRUE(all.equal(unname(ar$S[, 2]), 10 * log10(as.numeric(ar_reference$spec))))
)
ar_all_missing <- estimate(rep(NA_real_, 100), method = "autoregressive")
stopifnot(all(is.na(ar_all_missing$S)),
          isTRUE(all.equal(ar_all_missing$f, ar_reference$freq / dt)))
