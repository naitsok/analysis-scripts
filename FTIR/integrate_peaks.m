%% Desctiption
% Reads Fourier Transform Infrared Spectrum from CSV file and 
% calculated specified peak integrals
% Copy this script to directory with CSV files
clear all; close all;

%% General parameters
% directory with FTIR spectrum files, now they are stored in Data folder
% near which this file is located
% base_dir = uigetdir();
base_dir = '.\Data';
files = [...
    "SJ0127Ppp8.csv"...
    "SJ0127Ppp9.csv"...
    "SJ0127Ppp10.csv"...
    "SJ0127Ppp11.csv"...
    ];
% peak_limits: array of pair of wavenumbers that specify peak limits
peak_limits = [...
    520 756; ... % cm-1, Si-Hx deformation
    756 956; ... % cm-1, O-SiHx (840, 870 cm-1), Si-H2 scissoring (915 cm-1)
    991 1280; ... % cm-1, Si-O-Si
    1910 2310; ... % cm-1, Si-Hx stretching
    ];
% peak_titles: array of titles for the peaks
peak_titles = ["Si-Hx" "O-SiHx, Si-H2" "Si-O-Si" "Si-Hx"];
% peak_bl_points: array of pair ofnumber of points to take from each side 
% of peak for baseline, not used for now
peak_bl_points = [...
    0 0; ... % Si-Hx
    0 0; ... % O-SiHx, Si-H2
    0 20; ... % Si-O-Si
    20 20; ... % Si-Hx
    ];
% masses of samples, mg
sample_masses = [1.8 1.2 1.1 1.3];

%% Variables to keep spectra and results

spectra = cell(length(files), 1);
% spectral resolutions for each spectrum; needed to compare the spectra
% with different resolution
% for now assumption is that all spectra have the same resolution
% resolutions = zeros(length(files), 1); 
peak_integrals = zeros(length(files), size(peak_limits, 1));

%% Analysis

for i = 1:length(files)
    disp(files(i));
    
    % read the each spectrum from CSV file and store it in the cell array
    spectra{i} = table2array(readtable(convertStringsToChars(fullfile(base_dir, files(i)))));
    
    % loop through peaks
    for j = 1:size(peak_limits, 1)
        % select the absorbance values for each peak limits
        peak = spectra{i}(spectra{i}(:, 1) >= peak_limits(j, 1) & spectra{i}(:, 1) <= peak_limits(j, 2), 2);
        % inegrate peak and divide by sample mass
        peak_integrals(i, j) = trapz(peak) / sample_masses(i);
    end
    % show the resutls in console
    disp(peak_titles);
    disp(peak_integrals(i, :));
end

%% Plot spectra
    
ncols = 4;
nrows = round(length(spectra) / ncols);

% plot for peaks and fitting
figure('Position', [0 50 1800 950]);
for i = 1:length(spectra)
    subplot(nrows, ncols, i);
    % divide the absorbance values by sample mass for better visual
    % comparison
    plot(spectra{i}(:, 1), spectra{i}(:, 2) ./ sample_masses(i));
    title(files(i));
    xlabel('Wavenumber (cm-1)');
    ylabel('Absorbance (a.u./mg)');
end

