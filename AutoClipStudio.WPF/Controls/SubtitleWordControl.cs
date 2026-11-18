using System.Windows;
using System.Windows.Controls;

namespace AutoClipStudio.WPF.Controls;

/// <summary>
/// Custom control for displaying a single subtitle word with karaoke state.
/// </summary>
public class SubtitleWordControl : Control
{
    static SubtitleWordControl()
    {
        DefaultStyleKeyProperty.OverrideMetadata(typeof(SubtitleWordControl), new FrameworkPropertyMetadata(typeof(SubtitleWordControl)));
    }

    #region Dependency Properties

    public static readonly DependencyProperty WordTextProperty =
        DependencyProperty.Register(nameof(WordText), typeof(string), typeof(SubtitleWordControl), new PropertyMetadata(""));

    public string WordText
    {
        get => (string)GetValue(WordTextProperty);
        set => SetValue(WordTextProperty, value);
    }

    public static readonly DependencyProperty StateProperty =
        DependencyProperty.Register(nameof(State), typeof(SubtitleWordState), typeof(SubtitleWordControl), new PropertyMetadata(SubtitleWordState.Pending));

    public SubtitleWordState State
    {
        get => (SubtitleWordState)GetValue(StateProperty);
        set => SetValue(StateProperty, value);
    }

    public static readonly DependencyProperty ConfidenceProperty =
        DependencyProperty.Register(nameof(Confidence), typeof(double), typeof(SubtitleWordControl), new PropertyMetadata(1.0));

    public double Confidence
    {
        get => (double)GetValue(ConfidenceProperty);
        set => SetValue(ConfidenceProperty, value);
    }

    public static readonly DependencyProperty IsCorrectedProperty =
        DependencyProperty.Register(nameof(IsCorrected), typeof(bool), typeof(SubtitleWordControl), new PropertyMetadata(false));

    public bool IsCorrected
    {
        get => (bool)GetValue(IsCorrectedProperty);
        set => SetValue(IsCorrectedProperty, value);
    }

    public static readonly DependencyProperty OriginalWordProperty =
        DependencyProperty.Register(nameof(OriginalWord), typeof(string), typeof(SubtitleWordControl), new PropertyMetadata(null));

    public string? OriginalWord
    {
        get => (string?)GetValue(OriginalWordProperty);
        set => SetValue(OriginalWordProperty, value);
    }

    #endregion
}

public enum SubtitleWordState
{
    Pending,
    Active,
    Done,
    Corrected,
    LowConfidence
}