#' Calculate spectrograms (power spectral density estimates) from time series.
#'
#' This function creates spectrograms from seismic signals. It supports the
#' standard spectrogram approach and the Welch method.
#'
#' Only complete windows with finite samples are estimated. Windows overlapping
#' missing samples retain their time positions and have missing spectra.
#' The frequency axis is in Hz. The ordinates use the legacy stats::spectrum
#' scaling for a numeric vector before conversion to dB.
#'
#' @param data \code{Numeric} vector or list of vectors, seismic signal to
#' be processed.
#'
#' @param time \code{POSIX.ct} vector with time values. If omitted, an
#' artificial time vector will be created, based on \code{dt}. Only needed
#' if \code{data} is no \code{eseis} object.
#'
#' @param dt \code{Numeric} value, sampling period. If omitted, either
#' estimated from \code{time} or set to 0.005 s (200 Hz). Only needed
#' if \code{data} is no \code{eseis} object.
#'
#' @param Welch \code{Logical} value, option to use the Welch method for
#' calculations.
#'
#' @param window \code{Numeric} value, time window length in seconds used to
#' calculate individual spectra. Set to 1 percent of the time series length
#' by default.
#'
#' @param overlap \code{Numeric} value, fraction of window overlap.
#'
#' @param window_sub \code{Numeric} value, length of the sub-window in seconds
#' used to calculate spectra. Only relevant if \code{Welch = TRUE}. If omitted,
#' the sub-window length is set to 10 percent of the main window length.
#'
#' @param overlap_sub \code{Numeric} value, fraction of sub-window overlap.
#'
#' @param method  \code{Character} value, method to calculate the spectra.
#' One out of \code{"periodogram"} and \code{"autoregressive"}.
#' Default is \code{"periodogram"}.
#'
#' @param cpu \code{Numeric} value between 0 and 1, fraction of CPU cores to
#' use. If omitted, only one CPU is used.
#'
#' @param plot \code{Logical} value, toggle plot output. Default is
#' \code{FALSE}. For more customised plotting see \code{plot_spectrogram}.
#'
#' @param \dots Additional arguments passed to the function.
#'
#' @return \code{List} with spectrogram matrix, time and frequency vectors.
#'
#' @author Michael Dietze
#'
#' @keywords eseis
#'
#' @examples
#'
#' ## load example data set
#' data("earthquake")
#'
#' ## calculate and plot PSD straight away
#' P <- signal_spectrogram(data = s$BHZ,
#'                                time = t,
#'                                dt = 1 / 200,
#'                                plot = TRUE)
#'
#' ## calculate and plot PSD with defined window sizes and the Welch method
#' P <- signal_spectrogram(data = s$BHZ,
#'                                time = t,
#'                                dt = 1 / 200,
#'                                window = 5,
#'                                overlap = 0.9,
#'                                window_sub = 3,
#'                                overlap_sub = 0.9,
#'                                Welch = TRUE,
#'                                plot = TRUE)
#'
#' @export signal_spectrogram

signal_spectrogram <- function(

  data,
  time,
  dt,
  Welch = FALSE,
  window,
  overlap = 0.5,
  window_sub,
  overlap_sub = 0.5,
  method = "periodogram",
  cpu = NULL,
  plot = FALSE,
  ...

) {

  ## check data structure
  if(class(data)[1] == "list") {

    ## apply function to list
    data_out <- lapply(X = data,
                       FUN = eseis::signal_spectrogram,
                       time = time,
                       dt = dt,
                       Welch = Welch,
                       window = window,
                       overlap = overlap,
                       window_sub = window_sub,
                       overlap_sub = overlap_sub,
                       method = method,
                       cpu = cpu,
                       plot = plot)

    ## return output
    return(data_out)

  } else {

    ## check/store presence of time vector
    if(missing(time) == TRUE) {

      time_in <- NULL
    } else {

      time_in <- time
    }

    ## check/set dt
    if(missing(dt) == TRUE && class(data)[1] != "eseis") {

      if(missing(time) == TRUE) {

        dt <- 1 / 200

        warning("No dt provided. Set to 1 / 200 s by default!")

      } else {

        if(length(time) > 1000) {

          time_dt <- time[1:1000]

        } else {

          time_dt <- time

        }

        dt_estimate <- mean(x = diff(x = as.numeric(time)),
                            na.rm = TRUE)
        print(paste("dt estimated from time vector (",
                    signif(x = dt_estimate),
                    " s)",
                    sep = ""))

        dt <- dt_estimate
      }

    } else if(class(data)[1] == "eseis") {

      dt <- data$meta$dt
    }

    ## handle missing time vector
    if(missing(time) == TRUE && class(data)[1] != "eseis") {

      time <- seq(from = as.POSIXct(x = strptime(x = "0000-01-01 00:00:00",
                                                 format = "%Y-%m-%d %H:%M:%S",
                                                 tz = "UTC"), tz = "UTC"),
                  by = dt,
                  length.out = length(data))

      print("No or non-POSIXct time data provided. Default data generated!")

    } else if(class(data)[1] == "eseis") {

      time <- seq(from = data$meta$starttime,
                  by = data$meta$dt,
                  length.out = data$meta$n)
    }

    ## handle missing window length
    if(missing(window) == TRUE) {

      window <- 0.01 * length(time) * dt
    }

    ## handle missing sub-window length
    if(Welch == TRUE && missing(window_sub) == TRUE) {

      window_sub <- 0.1 * window

    } else if(Welch == FALSE) {

      window_sub <- NULL
    }

    ## get start time
    eseis_t_0 <- Sys.time()

    ## collect function arguments
    eseis_arguments <- list(data = "",
                            time = time_in,
                            dt = dt,
                            Welch = Welch,
                            window = window,
                            overlap = overlap,
                            window_sub = window_sub,
                            overlap_sub = overlap_sub,
                            method = method,
                            cpu = cpu,
                            plot = plot)

    ## homogenise data structure
    if(class(data)[1] == "eseis") {

      ## set eseis flag
      eseis_class <- TRUE

      ## store initial object
      eseis_data <- data

      ## extract signal vector
      data <- eseis_data$signal

    } else {

      ## set eseis flag
      eseis_class <- FALSE
    }

    ## change method keywords
    if(method == "periodogram") {

      method <- "pgram"
    }

    if(method == "autoregressive") {

      method <- "ar"
    }

    # Window the signal and estimate spectra

    ## get window length
    length_window <- round(x = window * (1 / dt),
                           digits = 0)

    ## get overlap length
    length_overlap <- round(x = length_window * overlap,
                            digits = 0)

    ## calculate indices for slicing the time series
    l_step <- length_window - length_overlap
    if(length_window < 2 || length_window > length(data) || l_step < 1) {
      stop("Set a window of at least two samples that fits the signal, with a positive step.")
    }
    slice_start <- seq(from = 1, to = length(data) - length_window + 1,
                       by = l_step)

    # Count invalid samples between each window's first and last sample.
    missing_count <- c(0, cumsum(!is.finite(data)))
    valid <- missing_count[slice_start + length_window] == missing_count[slice_start]
    data_list <- lapply(slice_start[valid], function(start) {
      data[start:(start + length_window - 1)]
    })
    if(!any(valid)) {
      # A deterministic signal supplies the estimator's frequency grid when all windows are missing.
      data_list <- list(cos(seq_len(length_window)))
    }

    ## define generic function to get spectra
    spec_generic <- function(x, method) {

      estimate <- stats::spectrum(x = x, method = method, plot = FALSE)
      list(power = estimate$spec, frequency = estimate$freq)

    }

    ## define generic function for Welch method to get spectra
    spec_welch <- function(x, window_sub, overlap_sub, dt, method) {

      ## get sub-window length
      length_window_sub <- round(x = window_sub * (1 / dt),
                                 digits = 0)

      ## get overlap length
      length_overlap_sub <- round(x = length_window_sub * overlap_sub,
                                  digits = 0)

      ## calculate indices for slicing the time series
      l_step <- length_window_sub - length_overlap_sub
      if(length_window_sub < 2 || length_window_sub > length(x) || l_step < 1) {
        stop("Set a Welch sub-window of at least two samples that fits the window, with a positive step.")
      }
      slice_start <- seq(from = 1,
                         to = length(x) - length_window_sub + 1,
                         by = l_step)

      ## convert time series to matrix with slices
      data_list_sub <- vector(mode = "list",
                              length = length(slice_start))

      for (i in 1:length(data_list_sub)) {

        data_list_sub[[i]] <- x[slice_start[i]:(slice_start[i] +
                                                  length_window_sub - 1)]
      }

      ## calculate spectra
      S_welch <- lapply(X = data_list_sub,
                        FUN = spec_generic,
                        method = method)

      power <- do.call(cbind, lapply(S_welch, function(estimate) estimate$power))
      list(power = rowMeans(power, na.rm = TRUE),
           frequency = S_welch[[1]]$frequency)

    }

    ## initiate cluster
    if(is.null(cpu) == FALSE) {

      cores <- parallel::detectCores()

      if(is.null(cpu) == FALSE) {

        n_cpu <- floor(cores * cpu)
        cores <- ifelse(cores < n_cpu, cores, n_cpu)
      } else {

        cores <- 1
      }
      cl <- parallel::makeCluster(getOption("mc.cores", cores))
    } else {

      cores <- 0
    }

    ## calculate spectra for each slice
    if(Welch == FALSE) {

      if(cores > 1) {

        ## non-Welch option in parallel mode
        S <- parallel::parLapply(cl = cl,
                                 X = data_list,
                                 fun = spec_generic,
                                 method = method)
      } else {

        ## non-Welch option in one-core mode
        S <- lapply(X = data_list,
                    FUN = spec_generic,
                    method = method)
      }
    } else {

      if(cores > 1) {

        ## Welch option in parallel processing mode
        S <- parallel::parLapply(cl = cl,
                                 X = data_list,
                                 fun = spec_welch,
                                 window_sub = window_sub,
                                 overlap_sub = overlap_sub,
                                 dt = dt,
                                 method = method)
      } else {

        ## Welch option in one-core mode
        S <- lapply(X = data_list,
                    FUN = spec_welch,
                    window_sub = window_sub,
                    overlap_sub = overlap_sub,
                    dt = dt,
                    method = method)
      }
    }

    ## stop cluster
    if(cores > 1) {

      parallel::stopCluster(cl = cl)
    }

    # The estimator returns frequencies in cycles per sample.
    f_spectrum <- S[[1]]$frequency / dt
    power <- matrix(NA_real_, nrow = length(f_spectrum), ncol = length(slice_start))
    if(any(valid)) {
      power[, valid] <- do.call(cbind, lapply(S, function(estimate) estimate$power))
    }

    # Convert spectral power to decibels.
    S <- 10 * log10(power)
    t_spectrum <- time[slice_start]
    rownames(S) <- f_spectrum
    colnames(S) <- t_spectrum

    ## assign output
    S <- list(S = S,
              t = t_spectrum,
              f = f_spectrum)
    class(S)[1] <- "spectrogram"

    ## optionally plot spectrogram
    if(plot == TRUE) {

      plot_spectrogram(data = S, ...)

    }

    ## optionally rebuild eseis object
    if(eseis_class == TRUE) {

      ## assign aggregated signal vector
      eseis_data <- list(PSD = S,
                         history = eseis_data$history)

      ## calculate function call duration
      eseis_duration <- as.numeric(difftime(time1 = Sys.time(),
                                            time2 = eseis_t_0,
                                            units = "secs"))

      ## update object history
      eseis_data$history[[length(eseis_data$history) + 1]] <-
        list(time = Sys.time(),
             call = "signal_spectrogram()",
             arguments = eseis_arguments,
             duration = eseis_duration)
      names(eseis_data$history)[length(eseis_data$history)] <-
        as.character(length(eseis_data$history))

      ## update data type
      eseis_data$meta$type = "spectrogram"

      ## set S3 class name
      class(eseis_data)[1] <- "eseis"

      ## assign eseis object to output data set
      S <- eseis_data
    }

    ## return output
    return(S)
  }
}
