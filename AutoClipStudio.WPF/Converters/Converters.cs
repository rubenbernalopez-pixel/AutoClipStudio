using System;
using System.Globalization;
using System.Windows;
using System.Windows.Data;
using System.Windows.Media;

namespace AutoClipStudio.WPF.Converters;

/// <summary>
/// Converts boolean to Visibility.
/// </summary>
public class BoolToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool b)
        {
            return b ? Visibility.Visible : Visibility.Collapsed;
        }
        return Visibility.Collapsed;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is Visibility v)
        {
            return v == Visibility.Visible;
        }
        return false;
    }
}

/// <summary>
/// Converts boolean to Accent Brush.
/// </summary>
public class BoolToAccentBrushConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool b && Application.Current != null)
        {
            return b
                ? Application.Current.Resources["AccentBrush"]
                : Application.Current.Resources["SurfaceBorderBrush"];
        }
        return Brushes.Transparent;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts score (0-1) to color brush.
/// </summary>
public class ScoreToColorConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double score && Application.Current != null)
        {
            if (score >= 0.8)
                return Application.Current.Resources["SuccessBrush"];
            if (score >= 0.6)
                return Application.Current.Resources["WarningBrush"];
            if (score >= 0.4)
                return Application.Current.Resources["InfoBrush"];
            return Application.Current.Resources["ErrorBrush"];
        }
        return Application.Current.Resources["TextMutedBrush"];
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts score (0-1) to percentage string.
/// </summary>
public class ScoreToPercentConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double score)
        {
            return $"{(int)(score * 100)}%";
        }
        return "0%";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts seconds to timecode string.
/// </summary>
public class TimecodeConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double seconds)
        {
            var ts = TimeSpan.FromSeconds(seconds);
            if (ts.Hours > 0)
                return $"{ts.Hours:00}:{ts.Minutes:00}:{ts.Seconds:00}";
            return $"{ts.Minutes:00}:{ts.Seconds:00}";
        }
        return "00:00";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts time range to display string.
/// </summary>
public class TimeRangeConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is Clip clip)
        {
            var start = TimeSpan.FromSeconds(clip.Start);
            var end = TimeSpan.FromSeconds(clip.End);
            var startStr = start.Hours > 0 ? $"{start.Hours:00}:{start.Minutes:00}:{start.Seconds:00}" : $"{start.Minutes:00}:{start.Seconds:00}";
            var endStr = end.Hours > 0 ? $"{end.Hours:00}:{end.Minutes:00}:{end.Seconds:00}" : $"{end.Minutes:00}:{end.Seconds:00}";
            return $"{startStr} - {endStr}";
        }
        return "";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts layout type to display name.
/// </summary>
public class LayoutToDisplayNameConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        return value?.ToString() switch
        {
            "solo_podcast" => "Solo pódcast",
            "balls_hoops" => "Pelotas y aros",
            "block_parkour" => "Parkour de bloques",
            "my_gameplay" => "Mi gameplay",
            _ => value?.ToString() ?? ""
        };
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Inverts boolean.
/// </summary>
public class InverseBoolConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool b)
            return !b;
        return true;
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is bool b)
            return !b;
        return false;
    }
}

/// <summary>
/// Converts double to formatted string with unit.
/// </summary>
public class DoubleToStringConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double d)
        {
            var unit = parameter?.ToString() ?? "";
            return $"{d:F1}{unit}";
        }
        return "";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Converts duration to short string (e.g., "1m 30s").
/// </summary>
public class DurationToStringConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        if (value is double seconds)
        {
            var ts = TimeSpan.FromSeconds(seconds);
            if (ts.Hours > 0)
                return $"{ts.Hours}h {ts.Minutes}m";
            if (ts.Minutes > 0)
                return $"{ts.Minutes}m {ts.Seconds}s";
            return $"{ts.Seconds}s";
        }
        return "0s";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        throw new NotImplementedException();
    }
}

/// <summary>
/// Multi-converter for progress ring stroke dash array.
/// </summary>
public class ProgressRingConverter : IMultiValueConverter
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