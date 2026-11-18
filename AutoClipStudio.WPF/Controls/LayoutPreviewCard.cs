using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace AutoClipStudio.WPF.Controls;

/// <summary>
/// Custom control for displaying a layout preview card.
/// </summary>
public class LayoutPreviewCard : Control
{
    static LayoutPreviewCard()
    {
        DefaultStyleKeyProperty.OverrideMetadata(typeof(LayoutPreviewCard), new FrameworkPropertyMetadata(typeof(LayoutPreviewCard)));
    }

    #region Dependency Properties

    public static readonly DependencyProperty TypeProperty =
        DependencyProperty.Register(nameof(Type), typeof(string), typeof(LayoutPreviewCard), new PropertyMetadata(""));

    public string Type
    {
        get => (string)GetValue(TypeProperty);
        set => SetValue(TypeProperty, value);
    }

    public static readonly DependencyProperty NameProperty =
        DependencyProperty.Register(nameof(Name), typeof(string), typeof(LayoutPreviewCard), new PropertyMetadata(""));

    public string Name
    {
        get => (string)GetValue(NameProperty);
        set => SetValue(NameProperty, value);
    }

    public static readonly DependencyProperty DisplayNameProperty =
        DependencyProperty.Register(nameof(DisplayName), typeof(string), typeof(LayoutPreviewCard), new PropertyMetadata(""));

    public string DisplayName
    {
        get => (string)GetValue(DisplayNameProperty);
        set => SetValue(DisplayNameProperty, value);
    }

    public static readonly DependencyProperty DescriptionProperty =
        DependencyProperty.Register(nameof(Description), typeof(string), typeof(LayoutPreviewCard), new PropertyMetadata(""));

    public string Description
    {
        get => (string)GetValue(DescriptionProperty);
        set => SetValue(DescriptionProperty, value);
    }

    public static readonly DependencyProperty PreviewImageProperty =
        DependencyProperty.Register(nameof(PreviewImage), typeof(string), typeof(LayoutPreviewCard), new PropertyMetadata(null));

    public string? PreviewImage
    {
        get => (string?)GetValue(PreviewImageProperty);
        set => SetValue(PreviewImageProperty, value);
    }

    public static readonly DependencyProperty IsSplitScreenProperty =
        DependencyProperty.Register(nameof(IsSplitScreen), typeof(bool), typeof(LayoutPreviewCard), new PropertyMetadata(false));

    public bool IsSplitScreen
    {
        get => (bool)GetValue(IsSplitScreenProperty);
        set => SetValue(IsSplitScreenProperty, value);
    }

    public static readonly DependencyProperty HasBackgroundProperty =
        DependencyProperty.Register(nameof(HasBackground), typeof(bool), typeof(LayoutPreviewCard), new PropertyMetadata(false));

    public bool HasBackground
    {
        get => (bool)GetValue(HasBackgroundProperty);
        set => SetValue(HasBackgroundProperty, value);
    }

    public static readonly DependencyProperty BackgroundDisplayNameProperty =
        DependencyProperty.Register(nameof(BackgroundDisplayName), typeof(string), typeof(LayoutPreviewCard), new PropertyMetadata(""));

    public string BackgroundDisplayName
    {
        get => (string)GetValue(BackgroundDisplayNameProperty);
        set => SetValue(BackgroundDisplayNameProperty, value);
    }

    public static readonly DependencyProperty TypeDisplayNameProperty =
        DependencyProperty.Register(nameof(TypeDisplayName), typeof(string), typeof(LayoutPreviewCard), new PropertyMetadata(""));

    public string TypeDisplayName
    {
        get => (string)GetValue(TypeDisplayNameProperty);
        set => SetValue(TypeDisplayNameProperty, value);
    }

    public static readonly DependencyProperty IsSelectedProperty =
        DependencyProperty.Register(nameof(IsSelected), typeof(bool), typeof(LayoutPreviewCard), new PropertyMetadata(false));

    public bool IsSelected
    {
        get => (bool)GetValue(IsSelectedProperty);
        set => SetValue(IsSelectedProperty, value);
    }

    #endregion
}