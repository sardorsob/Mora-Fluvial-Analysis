#' Clip and interpolate a spectrogram, with optional smoothing
#'
#' The function interpolates the power values in the frequency range defined
#' by the user, applying a spline interpolator. This function can be used to
#' extract a given frequency range or frequency band from a PSD. The former is
#' useful for convenient preparation of the \code{fmi_} function family to
#' achieve fluvial model inversion workflows. The latter is useful to create
#' seismic power time series for a given frequency band.
#'
#' @param data Spectrogram from \code{signal_spectrogram}, an equivalent object,
#' or a numeric matrix. Frequency labels in matrix row names are used when
#' available.
#'
#' @param f \code{Numeric} vector of length two, frequency range to which
#' the PSD will be clipped. Alternatively, an empirical frequency vector can
#' be submitted, too (e.g., when non-uniformly spaced frequencies are used).
#'
#' @param res \code{Numeric} value, number of frequency values used as output
#' of the frequency interpolation. If set to \code{1},
#' the input frequency range (\code{f}) will be averaged and a
#' \code{data frame} with the elements \code{time} and \code{power} will
#' be returned. The mean uses the supplied values, including dB for a
#' spectrogram from \code{signal_spectrogram}.
#'
#' @param n \code{Numeric} value, number of values to use in a running average
#' filter to smoothen the interpolated output. If omitted, the spectrogram
#' will not be changed apart from the interpolation option.
#'
#' @param dt \code{Numeric} value, sampling interval. Required only for an
#' unlabeled matrix, where the rows are assumed to span zero to Nyquist.
#'
#' @return A clipped and interpolated spectrogram, or a data frame with
#' a time series of an averaged frequency band.
#'
#' @author Michael Dietze
#'
#' @keywords eseis
#'
#' @examples
#'
#' ## load example data
#' data(rockfall)
#'
#' ## calculate spectrogram
#' psd <- signal_spectrogram(data = rockfall_eseis)
#'
#' ## Example 1: interpolate PSD to 5 to 15 Hz with 100 values resolution
#' psd_int <- aux_clipspectrogram(data = psd, f = c(5, 15), res = 100)
#'
#' ## plot output
#' plot(psd_int)
#'
#' ## Example 2: interpolate PSD using user defined frequency vector
#' psd_int <- aux_clipspectrogram(data = psd, f = sort(runif(n = 20, 5, 20)))
#'
#' ## plot output
#' plot(psd_int)
#'
#' ## Example 3: interpolate non-eseis matrix object
#' psd_int <- aux_clipspectrogram(data = psd$PSD$S,
#'                                f = c(0, 10),
#'                                res = 10,
#'                                dt = 1/50)
#'
#' ## Example 4: extract a power time series for a frequency band
#' p_ts <- aux_clipspectrogram(data = psd, f = c(5, 10), res = 1)
#' plot(p_ts, type = "l")
#'
#' ## Example 5: clip and smoothen the output
#' p_sm <- aux_clipspectrogram(data = psd, f = c(5, 20), res = 50, n = 10)
#' plot(p_sm)
#'
#' @export aux_clipspectrogram

aux_clipspectrogram <- function(

  data,
  f,
  res = 100,
  n,
  dt

) {

  is_eseis <- inherits(data, "eseis")
  is_spectrogram <- is.list(data) && !is.data.frame(data)
  if(is_eseis || is_spectrogram) {
    spectrogram <- if(is_eseis) data$PSD else data
    p <- spectrogram$S
    f_emp <- spectrogram$f
    time <- spectrogram$t
  } else {
    p <- data
    f_emp <- suppressWarnings(as.numeric(rownames(p)))
    if(length(f_emp) != nrow(p) || any(!is.finite(f_emp))) {
      if(missing(dt)) stop("Provide dt for a matrix without frequency labels.")
      f_emp <- seq(from = 0, to = 1 / dt / 2, length.out = nrow(p))
    }
    time <- seq_len(ncol(p))
  }

  ## check/set interpolation frequency vector
  if(length(f) == 2) {

    ## check correct order of frequency limits
    if(f[1] >= f[2]) {

      stop("Lower frequency is not smaller than higher!")
    }

    ## build frequency vector
    f_int <- seq(from = f[1], to = f[2], length.out = res)

  } else {

    f_int <- f
  }

  ## average or interpolate data set
  if(res == 1) {

    # Average the power of bins in the selected band at each time.
    p_avg <- colMeans(p[f_emp >= f[1] & f_emp <= f[2], , drop = FALSE])

    data <- data.frame(time = time, power = p_avg)

    ## optionally smoothen data set
    if(missing(n) == FALSE) {

      data$power <- caTools::runmean(x = data$power, k = n)
    }

  } else {

    # Preserve missing windows in the clipped spectrogram.
    p_clip <- vapply(seq_len(ncol(p)), function(column) {
      power <- p[, column]
      if(sum(is.finite(power)) < 2) return(rep(NA_real_, length(f_int)))
      spline(x = f_emp, y = power, xout = f_int)$y
    }, numeric(length(f_int)))

    dim(p_clip) <- c(length(f_int), ncol(p))

    if(!missing(n)) {
      p_clip <- vapply(seq_len(ncol(p_clip)), function(column) {
        caTools::runmean(x = p_clip[, column], k = n)
      }, numeric(length(f_int)))
      dim(p_clip) <- c(length(f_int), ncol(p))
    }

    if(is_eseis) {
      data$PSD$S <- p_clip
      data$PSD$f <- f_int
    } else if(is_spectrogram) {
      data$S <- p_clip
      data$f <- f_int
    } else {
      data <- p_clip
    }
  }

  ## return output
  return(data)
}
