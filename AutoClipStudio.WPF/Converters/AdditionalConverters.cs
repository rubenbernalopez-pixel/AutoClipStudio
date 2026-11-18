using System;
using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace AutoClipStudio.WPF.Converters;

/// <summary>
/// Converts stage name to brush for progress indicators.
/// </summary>
public class StageToBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is string stage && parameter is string targetStage)
        {
            var isActive = stage.Equals(targetStage, StringComparison.OrdinalIgnoreCase);
            var isCompleted = GetStageOrder(stage) < GetStageOrder(targetStage);

            if (isActive)
                return Application.Current.Resources["AccentBrush"];
            if (isCompleted)
                return Application.Current.Resources["SuccessBrush"];

            return Application.Current.Resources["SurfaceBorderBrush"];
        }
        return Application.Current.Resources["SurfaceBorderBrush"];
    }

    private int GetStageOrder(string stage)
    {
        return stage.ToLowerInvariant() switch
        {
            "descargando" => 1,
            "downloading" => 1,
            "transcribiendo" => 2,
            "transcribing" => 2,
            "seleccionando" => 3,
            "selecting" => 3,
            "renderizando" => 4,
            "rendering" => 4,
            "subtítulos" => 5,
            "subtitles" => 5,
            _ => 0
        };
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts file path to folder name.
/// </summary>
public class PathToFolderNameConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is string path && !string.IsNullOrEmpty(path))
        {
            try
            {
                return System.IO.Path.GetDirectoryName(path) ?? path;
            }
            catch
            {
                return path;
            }
        }
        return "";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts double to string with 1 decimal.
/// </summary>
public class DoubleToStringOneDecimalConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double d)
        {
            return d.ToString("F1", culture);
        }
        return "0.0";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is string s && double.TryParse(s, NumberStyles.Float, culture, out double result))
        {
            return result;
        }
        return 0.0;
    }
}

/// <summary>
/// Converts clip score to descriptive text.
/// </summary>
public class ScoreToDescriptionConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double score)
        {
            return score switch
            {
                >= 0.85 => "Excelente - Muy alto potencial",
                >= 0.70 => "Muy bueno - Alto potencial",
                >= 0.55 => "Bueno - Potencial medio",
                >= 0.40 => "Regular - Potencial bajo",
                _ => "Bajo - Revisar manualmente"
            };
        }
        return "Sin evaluar";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Multi-converter for progress ring stroke dash array.
/// </summary>
public class ProgressRingStrokeDashArrayConverter : IMultiValueConverter
{
    public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
    {
        if (values.Length >= 2 &&
            values[0] is double percent &&
            values[1] is double diameter)
        {
            var circumference = Math.PI * diameter;
            var dash = (percent / 100.0) * circumference;
            var gap = circumference - dash;
            return $"{dash},{gap}";
        }
        return "0,100";
    }

    public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts bool to "Sí"/"No".
/// </summary>
public class BoolToSiNoConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool b)
        {
            return b ? "Sí" : "No";
        }
        return "No";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is string s)
        {
            return s.Equals("Sí", StringComparison.OrdinalIgnoreCase);
        }
        return false;
    }
}

/// <summary>
/// Converts int count to plural suffix.
/// </summary>
public class PluralConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is int count)
        {
            return count == 1 ? "" : "s";
        }
        return "";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts hashtags list to preview string.
/// </summary>
public class HashtagsToPreviewConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is System.Collections.IList list && list.Count > 0)
        {
            var tags = list.Cast<string>().Take(3).ToArray();
            return string.Join(" ", tags) + (list.Count > 3 ? $" +{list.Count - 3}" : "");
        }
        return "";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}